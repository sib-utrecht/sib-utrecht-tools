import boto3
from time import sleep
import json
import logging
import sys

from ..conscribo.list_relations import list_relations_members
from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict
from ..cognito.list_users import (
    list_all_cognito_users,
    cognito_user_to_canonical,
    canonical_to_cognito_user,
    cognito_client,
    user_pool_id,
)


logging.basicConfig(filename="cognito_sync.log", level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def sync_conscribo_to_cognito(dry_run=True):
    cognito_users = list_all_cognito_users()
    
    print(f"Users count: {len(cognito_users)}")
    assert len(cognito_users) > 5, "No users found in the Cognito user pool."

    # print(json.dumps(cognito_users[0], default=str, indent=2))
    print()

    cognito_users = [cognito_user_to_canonical(user) for user in cognito_users]

    conscribo_members = list_relations_members()
    print(f"Conscribo members count: {len(conscribo_members)}")

    cognito_without_id = [
        user
        for user in cognito_users
        if user.get("conscribo_id") is None or len(user["conscribo_id"]) == 0
    ]

    cognito_by_id = {
        user["conscribo_id"]: user
        for user in cognito_users
        if user.get("conscribo_id") is not None and len(user["conscribo_id"]) > 0
    }

    conscribo_by_id = {member["conscribo_id"]: member for member in conscribo_members}

    print("Without Conscribo ID:")
    print(", ".join(sorted([user["email"] for user in cognito_without_id])))

    print("Cognito:")
    print(", ".join(sorted(cognito_by_id.keys())))
    print()
    print("Conscribo:")
    print(", ".join(sorted(conscribo_by_id.keys())))
    print()
    print("Cognito only:")
    cognito_only = sorted(cognito_by_id.keys() - conscribo_by_id.keys())
    print(", ".join(sorted(cognito_only)))
    for cognito_id in cognito_only:
        print(f"{cognito_id}: {json.dumps(cognito_by_id[cognito_id], indent=2)}")

    print()
    print("Conscribo only:")
    conscribo_only = conscribo_by_id.keys() - cognito_by_id.keys()
    print(", ".join(sorted(conscribo_only)))
    for conscribo_id in conscribo_only:
        print(f"{conscribo_id}: {json.dumps(conscribo_by_id[conscribo_id], indent=2)}")
    print()

    def prune_users():
        logging.info(f"Dry run: {dry_run}")

        for conscribo_id in cognito_only:
            cognito_user = cognito_by_id[conscribo_id]
            cognito_basics = (
                cognito_user["first_name"],
                cognito_user["last_name"],
                cognito_user["email"],
            )

            logging.info(f"DELETE {conscribo_id} {json.dumps(cognito_basics)}")

            if dry_run:
                continue

            cognito_sub = cognito_user["cognito_sub"]

            cognito_client.admin_delete_user(
                UserPoolId=user_pool_id,
                Username=cognito_user["cognito_sub"],
            )
            logging.info(f"Deleted {conscribo_id} ({cognito_sub})")


    def create_users():
        for conscribo_id in conscribo_only:
            conscribo_user = conscribo_by_id[conscribo_id]

            email = conscribo_user.get("email", None)
            if email is None or len(email) == 0:
                logging.warning(
                    f"Skipping user '{conscribo_id}' due to missing e-mail address."
                )
                continue

            conscribo_basics = (
                conscribo_user["first_name"],
                conscribo_user["last_name"],
                conscribo_user["email"],
            )

            logging.info(f"CREATE {conscribo_id} {json.dumps(conscribo_basics)}")

            cognito_user = canonical_to_cognito_user(conscribo_user)

            print(json.dumps(cognito_user, indent=2))

            if dry_run:
                continue

            cognito_client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=cognito_user["Username"],
                UserAttributes=cognito_user["Attributes"],
                DesiredDeliveryMediums=["EMAIL"],
            )

    def update_users():
        for conscribo_id in conscribo_by_id.keys():
            cognito_user = cognito_by_id.get(conscribo_id, None)
            conscribo_user = conscribo_by_id[conscribo_id]

            if cognito_user is None:
                continue

            old_attributes = canonical_to_cognito_user(cognito_user)["Attributes"]
            old_attribute_values_by_name = {
                attr["Name"]: attr["Value"] for attr in old_attributes
            }

            # Update user attributes in Cognito based on Conscribo data
            new_attributes = canonical_to_cognito_user(conscribo_user)["Attributes"]

            update_attributes = []
            for attr in new_attributes:
                prev_value = old_attribute_values_by_name.get(attr["Name"], "")

                if prev_value == attr["Value"]:
                    # print(f"Skipping unchanged attribute {attr['Name']} for {conscribo_id}")
                    continue
                print(f"Changed {attr['Name']}: {prev_value} -> {attr['Value']} for {conscribo_id}")

                update_attributes.append(attr)

            if len(update_attributes) == 0:
                continue

            print(f"Updating attributes for {conscribo_id}: {update_attributes}")


            cognito_sub = cognito_user["cognito_sub"]
            logging.info(f"UPDATE {conscribo_id} {json.dumps(update_attributes)}\n")
            if dry_run:
                continue

            cognito_client.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=cognito_sub,
                UserAttributes=new_attributes,
            )
    
    prune_users()
    create_users()
    update_users()
