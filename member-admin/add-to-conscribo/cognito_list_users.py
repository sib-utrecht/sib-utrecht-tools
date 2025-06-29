import boto3
import canonical_key
from canonical_key import flatten_dict
from conscribo_list_relations import list_relations_members
from time import sleep
import json
import logging
import sys


# Print account id
# print(boto3.client("sts").get_caller_identity()["Account"])

logging.basicConfig(filename="cognito_sync.log", level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

cognito_client = boto3.client("cognito-idp", region_name="eu-central-1") 

user_pool_id = "eu-central-1_Ecd3uxa0G"

cognito_to_canonical_dict = canonical_key.get_cognito_to_key()

print(cognito_to_canonical_dict)
print("\n" * 2)


def cognito_user_meta_to_canonical(user):
    to_canonical = cognito_to_canonical_dict

    flattened_user = flatten_dict(user)
    canonical = dict()
    for (key, value) in flattened_user.items():
        new_key = to_canonical.get(key, None)

        if new_key is not None:
            canonical[new_key] = value
            continue

        other = canonical.setdefault("other", dict())
        other[key] = value

    return canonical

def cognito_user_to_canonical(user):
    username = user.get("Username")
    usercreatedate = user.get("UserCreateDate")
    userlastmodifieddate = user.get("UserLastModifiedDate")
    user_status = user.get("UserStatus")
    user_enabled = user.get("Enabled")

    attributes = user.pop("Attributes", [])
    attributes_dict = {attr["Name"]: attr["Value"] for attr in attributes}
    canonical = cognito_user_meta_to_canonical(attributes_dict)

    user["UserCreateDate"] = str(usercreatedate)
    user["UserLastModifiedDate"] = str(userlastmodifieddate)

    cleaned_user = {
        "meta": user,
        **canonical
    }

    return cleaned_user

def canonical_to_cognito_user(user):
    to_cognito = canonical_key.get_key_to_cognito()

    flattened_user = flatten_dict(user)
    attributes = []
    for (key, value) in flattened_user.items():
        new_key = to_cognito.get(key, None)

        if key == "email_verified":
            new_key = new_key or "email_verified"

        if new_key is None:
            logging.warning(f"[canonical_to_cognito_user] Key {key} not found in Cognito mapping, skipping.")
            continue

        attributes.append({
            "Name": new_key,
            "Value": value
        })

        # other = user.setdefault("other", dict())
        # other[key] = value

    return {
        "Username": user.get("cognito_sub") or user.get("email"),
        "Attributes": attributes,
    }


cognito_users = []

response = cognito_client.list_users(
    UserPoolId=user_pool_id,
    Limit=10,
)

while True:
    cognito_users.extend(response["Users"])

    paginationToken = response.get("PaginationToken")
    if paginationToken is None:
        break

    response = cognito_client.list_users(
        UserPoolId=user_pool_id,
        PaginationToken=paginationToken,
    )
    sleep(0.1)


print(f"Users count: {len(cognito_users)}")

assert len(cognito_users) > 5, "No users found in the Cognito user pool."

print(json.dumps(cognito_users[0], default=str, indent=2))
print()

cognito_users = [
    cognito_user_to_canonical(user)
    for user in cognito_users
]

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

conscribo_by_id = {
    member["conscribo_id"]: member
    for member in conscribo_members
}

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

dry_run = True


def prune_users():
    logging.info(f"Dry run: {dry_run}")

    for conscribo_id in cognito_only:
        cognito_user = cognito_by_id[conscribo_id]
        cognito_basics = (cognito_user["first_name"], cognito_user["last_name"], cognito_user["email"])

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
            logging.warning(f"Skipping user '{conscribo_id}' due to missing e-mail address.")
            continue

        conscribo_basics = (conscribo_user["first_name"], conscribo_user["last_name"], conscribo_user["email"])

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

create_users()

def update_users():
    # Check for updated e-mail addresses and other metadata
    raise NotImplementedError("Update users not implemented yet.")