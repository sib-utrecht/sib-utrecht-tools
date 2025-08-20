import boto3
from time import sleep
import json
import logging
import sys

from ..conscribo.relations import list_relations_members
from ..conscribo.groups import list_entity_groups
from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict
from ..cognito.list_users import (
    list_all_cognito_users,
    cognito_user_to_canonical,
    canonical_to_cognito_user,
    cognito_client,
    user_pool_id,
    list_cognito_users_canonical,
)
from ..cognito.groups import (
    cognito_list_groups,
    cognito_list_users_in_group,
)
from ..utils import increase_indent

logging.basicConfig(
    filename="cognito_sync_groups.log",
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("sib-tools")
logger.setLevel(logging.DEBUG)

logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('s3transfer').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


def sync_conscribo_to_cognito_groups(dry_run=True, logger: logging.Logger | None = None):
    logger = logger or logging.getLogger()
    cognito_groups = cognito_list_groups()
    logger.info(f"Groups count: {len(cognito_groups)}")
    logger.info(f"Dry run: {dry_run}")

    cognito_groups_by_name = {group["GroupName"]: group for group in cognito_groups}
    cognito_group_members = {
        group["GroupName"]: cognito_list_users_in_group(group["GroupName"])
        for group in cognito_groups
    }

    conscribo_groups = list_entity_groups()
    cognito_users = list_cognito_users_canonical()

    cognito_users_by_id = {user.get("conscribo_id"): user for user in cognito_users}
    cognito_users_by_id.pop(None, None)  # Remove any None key if it exists

    accounts_group = next(
        (a for a in conscribo_groups if a["name"] == "accounts"), None
    )

    if accounts_group is None:
        raise Exception(
            "Please create a Conscribo group called 'accounts', with "
            "subgroups for each member group you need on Cognito "
            "(like 'admins')"
        )

    subgroups = [a for a in conscribo_groups if a["parentId"] == accounts_group["id"]]
    subgroups.sort(key=lambda x: x["name"])

    logger.info(f"Found {len(subgroups)} subgroups on Conscribo:")
    for subgroup in subgroups:
        logger.info(
            f"  - {subgroup['name']} ({subgroup['id']}) with "
            f"{len(subgroup['members'])} members"
        )

    logger.info("")
    logger.info(f"Found {len(cognito_group_members)} groups on Cognito:")
    for name, members in sorted(cognito_group_members.items(), key=lambda x: x[0]):
        logger.info(f"  - {name} with {len(members)} members")
    logger.info("")

    for subgroup in subgroups:
        group_name = subgroup["name"]

        logger.info("")
        logger.info(f"Processing subgroup: {group_name} ({subgroup['id']})")

        if group_name not in cognito_group_members:
            logger.info(f"Creating Cognito group: {group_name}")
            if not dry_run:
                ans = cognito_client.create_group(
                    GroupName=group_name,
                    UserPoolId=user_pool_id,
                )
                logger.debug(json.dumps(ans, indent=2))
                logger.info(f"Created Cognito group: {ans['Group']}")
                sleep(0.1)
                cognito_group_members[group_name] = []

        cognito_members = [
            cognito_user_to_canonical(user)
            for user in cognito_group_members.get(group_name, [])
        ]

        conscribo_member_ids = {a["entityId"] for a in subgroup["members"]} - {None}
        cognito_member_ids = {a.get("conscribo_id") for a in cognito_members} - {None}

        to_add = conscribo_member_ids - cognito_member_ids
        to_remove = cognito_member_ids - conscribo_member_ids

        logger.info(
            f"Group {group_name} ({subgroup['id']}) has {len(subgroup['members'])} members"
        )
        logger.info(f"  - To add: {len(to_add)} members")
        logger.info(f"  - To remove: {len(to_remove)} members")

        for user_id in to_add:
            cognito_member = cognito_users_by_id.get(user_id, None)
            if cognito_member is None:
                logger.warning(
                    f"User {user_id} not found in Cognito users, skipping. "
                    f"Would add to group {group_name}"
                )
                continue

            username = cognito_member["cognito_sub"]
            email = cognito_member["email"]

            basic_info = (
                cognito_member["first_name"],
                cognito_member["last_name"],
                email,
                username,
            )

            logger.info(
                f"ADD {user_id} TO {group_name} "
                f"{json.dumps(basic_info)}"
            )
            if dry_run:
                continue

            res = cognito_client.admin_add_user_to_group(
                UserPoolId=user_pool_id,
                Username=username,
                GroupName=group_name,
            )
            logger.debug("Response from Cognito API:")
            logger.debug(increase_indent(json.dumps(res, indent=2)))

            sleep(0.1)

        for user_id in to_remove:
            found = False
            for cognito_member in cognito_members:
                if cognito_member.get("conscribo_id") != user_id:
                    continue
                found = True

                username = cognito_member["cognito_sub"]
                email = cognito_member["email"]

                basic_info = (
                    cognito_member["first_name"],
                    cognito_member["last_name"],
                    email,
                    username,
                )

                logger.info(
                    f"REMOVE {user_id} FROM {group_name} "
                    f"{json.dumps(basic_info)}"
                )
                if dry_run:
                    continue

                res = cognito_client.admin_remove_user_from_group(
                    UserPoolId=user_pool_id,
                    Username=username,
                    GroupName=group_name,
                )
                logger.debug("Response from Cognito API:")
                logger.debug(increase_indent(json.dumps(res, indent=2)))

                sleep(0.1)
            if not found:
                logger.warning(
                    f"User {user_id} not found in Cognito users, skipping. "
                    f"Would remove from group {group_name}"
                )
