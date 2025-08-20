import boto3
from time import sleep
import json
import logging
import sys

from sib_tools.conscribo.groups import find_group_id_by_name, get_group_members_cached

from ..conscribo.relations import list_relations_active_members
from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict
from ..cognito.list_users import (
    list_all_cognito_users,
    cognito_user_to_canonical,
    canonical_to_cognito_user,
    cognito_client,
    user_pool_id,
)
from ..utils import print_change_count, print_header

def sync_conscribo_to_cognito(
    dry_run=True, logger: logging.Logger | None = None
) -> int:
    logger = logger or logging.getLogger(__name__)

    print_header("Syncing Conscribo members to AWS Cognito users...", logger)

    if dry_run:
        logger.info(f"Dry run: {dry_run}")

    cognito_users = list_all_cognito_users()

    logger.debug(f"Cognito users count: {len(cognito_users)}")
    assert len(cognito_users) > 5, "No users found in the Cognito user pool."

    # logger.debug(json.dumps(cognito_users[0], default=str, indent=2))
    logger.info("")

    cognito_users = [cognito_user_to_canonical(user) for user in cognito_users]

    conscribo_members = list_relations_active_members()
    logger.debug(f"Conscribo members count: {len(conscribo_members)}")

    # Filter to only members who are not in the 'Te verwerken' Conscribo group
    te_verwerken_group_id = find_group_id_by_name("Te verwerken")
    if te_verwerken_group_id is None:
        logger.warning("Not excluding 'Te verwerken' members: the Conscribo group 'Te verwerken' as not found.")

    if te_verwerken_group_id is not None:
        group_members = get_group_members_cached(te_verwerken_group_id)

        prev_conscribo_members_count = len(conscribo_members)
        
        conscribo_members = [
            member for member in conscribo_members
            if member["conscribo_id"] not in group_members
        ]

        new_conscribo_members_count = len(conscribo_members)

        logger.info(
            f"Excluding {prev_conscribo_members_count - new_conscribo_members_count} members in 'Te verwerken' group"
        )

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

    logger.debug("Without Conscribo ID:")
    logger.debug(", ".join(sorted([user["email"] for user in cognito_without_id])))

    logger.debug("Cognito:")
    logger.debug(", ".join(sorted(cognito_by_id.keys())))
    logger.debug("")
    logger.debug("Conscribo:")
    logger.debug(", ".join(sorted(conscribo_by_id.keys())))
    logger.debug("")
    logger.debug("Cognito only:")
    cognito_only = sorted(cognito_by_id.keys() - conscribo_by_id.keys())
    logger.debug(", ".join(sorted(cognito_only)))

    logger.debug("")
    logger.debug("Conscribo only:")
    conscribo_only = conscribo_by_id.keys() - cognito_by_id.keys()
    logger.debug(", ".join(sorted(conscribo_only)))
    logger.debug("")

    change_count = 0

    def prune_users():
        nonlocal change_count

        for conscribo_id in cognito_only:
            cognito_user = cognito_by_id[conscribo_id]
            cognito_basics = (
                cognito_user["first_name"],
                cognito_user["last_name"],
                cognito_user["email"],
            )

            logger.info(f"DELETE {conscribo_id} {json.dumps(cognito_basics)}")
            change_count += 1

            if dry_run:
                continue

            cognito_sub = cognito_user["cognito_sub"]

            cognito_client.admin_delete_user(
                UserPoolId=user_pool_id,
                Username=cognito_user["cognito_sub"],
            )
            logger.info(f"Deleted {conscribo_id} ({cognito_sub})")

    def create_users():
        nonlocal change_count
        for conscribo_id in conscribo_only:
            conscribo_user = conscribo_by_id[conscribo_id]

            email = conscribo_user.get("email", None)
            if email is None or len(email) == 0:
                logger.warning(
                    f"Skipping user '{conscribo_id}' due to missing e-mail address."
                )
                continue

            conscribo_basics = (
                conscribo_user["first_name"],
                conscribo_user["last_name"],
                conscribo_user["email"],
            )

            logger.info(f"CREATE {conscribo_id} {json.dumps(conscribo_basics)}")
            change_count += 1

            cognito_user = canonical_to_cognito_user(conscribo_user)

            logger.debug(json.dumps(cognito_user, indent=2))

            if dry_run:
                continue

            cognito_client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=cognito_user["Username"],
                UserAttributes=cognito_user["Attributes"],
                DesiredDeliveryMediums=["EMAIL"],
            )

    def update_users():
        nonlocal change_count
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
                    # logger.debug(f"Skipping unchanged attribute {attr['Name']} for {conscribo_id}")
                    continue
                logger.info(
                    f"Changed {attr['Name']}: {prev_value} -> {attr['Value']} for {conscribo_id}"
                )

                update_attributes.append(attr)

            if len(update_attributes) == 0:
                continue

            # Count this as a single modification for the user
            change_count += 1
            logger.info(f"Updating attributes for {conscribo_id}: {update_attributes}")

            cognito_sub = cognito_user["cognito_sub"]
            logger.info(f"UPDATE {conscribo_id} {json.dumps(update_attributes)}\n")
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

    print_change_count(change_count, logger)
    return change_count
