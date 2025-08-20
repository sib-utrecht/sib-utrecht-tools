import logging
import sys
import json
from time import sleep

from sib_tools.utils import increase_indent, print_change_count, print_header

from ..conscribo.relations import list_relations_members
from ..conscribo.groups import list_entity_groups
from ..conscribo.groups import add_relations_to_group, remove_relations_from_group

from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict
from ..cognito.list_users import (
    list_all_cognito_users,
    cognito_user_to_canonical,
    canonical_to_cognito_user,
    cognito_client,
    user_pool_id,
)
from ..cognito.groups import (
    cognito_list_groups,
    cognito_list_users_in_group,
    cognito_list_users_in_group_canonical,
)

def sync_cognito_to_conscribo_groups(dry_run=True, logger: logging.Logger | None = None) -> int:
    logger = logger or logging.getLogger(__name__)

    print_header("Syncing Cognito groups to Conscribo groups...", logger)

    cognito_groups = cognito_list_groups()
    logger.info(f"Groups count: {len(cognito_groups)}")

    cognito_groups_by_name = {group["GroupName"]: group for group in cognito_groups}
    cognito_group_members = {
        group["GroupName"]: cognito_list_users_in_group_canonical(group["GroupName"])
        for group in cognito_groups
    }

    conscribo_groups = list_entity_groups()
    conscribo_groups_by_name = {g["name"]: g for g in conscribo_groups}

    accounts_group = next(
        (a for a in conscribo_groups if a["name"] == "accounts"), None
    )
    if accounts_group is None:
        raise Exception(
            "Please create a Conscribo group called 'accounts', with "
            "subgroups for each member group you need on Cognito (like 'admins')"
        )

    subgroups = [a for a in conscribo_groups if a["parentId"] == accounts_group["id"]]
    subgroups.sort(key=lambda x: x["name"])

    logger.info(f"Found {len(subgroups)} subgroups on Conscribo:")
    for subgroup in subgroups:
        logger.info(
            f"  - {subgroup['name']} ({subgroup['id']}) with {len(subgroup['members'])} members"
        )

    logger.info("")
    logger.info(f"Found {len(cognito_group_members)} groups on Cognito:")
    for name, members in sorted(cognito_group_members.items(), key=lambda x: x[0]):
        logger.info(f"  - {name} with {len(members)} members")
    logger.info("")
    logger.info("")

    change_count = 0

    # Now sync Cognito groups to Conscribo subgroups
    for group_name, cognito_members in cognito_group_members.items():
        conscribo_group = conscribo_groups_by_name.get(group_name)
        if not conscribo_group:
            logger.info(f"Group not found in Conscribo: '{group_name}', skipping.")
            continue

        conscribo_member_ids = set(a["entityId"] for a in conscribo_group["members"])

        cognito_member_ids = set(a["conscribo_id"] for a in cognito_members)

        to_add = cognito_member_ids - conscribo_member_ids
        to_remove = conscribo_member_ids - cognito_member_ids

        # Each creation (add) and deletion (remove) counts as a change
        change_count += len(to_add) + len(to_remove)

        if len(to_add) > 0:
            logger.info(
                f"ADD {','.join(sorted(to_add))} TO {group_name}"
            )

            if not dry_run:
                res = add_relations_to_group(
                    conscribo_group["id"],
                    list(to_add),
                )
                logger.debug("Response from Conscribo API:")
                logger.debug(increase_indent(json.dumps(res, indent=2)))

                logger.info(f"Added {len(to_add)} users to Conscribo group {group_name}")
                sleep(2)

        if len(to_remove) > 0:
            logger.info(
                f"REMOVE {','.join(sorted(to_remove))} FROM {group_name}"
            )

            if not dry_run:
                res = remove_relations_from_group(
                    conscribo_group["id"],
                    list(to_remove),
                )
                logger.debug("Response from Conscribo API:")
                logger.debug(increase_indent(json.dumps(res, indent=2)))

                logger.info(f"Removed {len(to_remove)} users from Conscribo group {group_name}")
                sleep(2)
        logger.info("")

    print_change_count(change_count, logger)
    return change_count

if __name__ == "__main__":
    sync_cognito_to_conscribo_groups(dry_run=True)
