import logging
import sys
import json
from time import sleep

from sib_tools.utils import increase_indent

from ..conscribo.list_relations import list_relations_members
from ..conscribo.list_groups import list_entity_groups
from ..conscribo.list_groups import add_relations_to_group, remove_relations_from_group

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

logging.basicConfig(
    filename="cognito_sync_groups_to_conscribo.log",
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("s3transfer").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

def sync_cognito_to_conscribo_groups(dry_run=True):
    cognito_groups = cognito_list_groups()
    logging.info(f"Groups count: {len(cognito_groups)}")

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

    logging.info(f"Found {len(subgroups)} subgroups on Conscribo:")
    for subgroup in subgroups:
        logging.info(
            f"  - {subgroup['name']} ({subgroup['id']}) with {len(subgroup['members'])} members"
        )

    logging.info("")
    logging.info(f"Found {len(cognito_group_members)} groups on Cognito:")
    for name, members in sorted(cognito_group_members.items(), key=lambda x: x[0]):
        logging.info(f"  - {name} with {len(members)} members")
    logging.info("")
    logging.info("")


    # Now sync Cognito groups to Conscribo subgroups
    for group_name, cognito_members in cognito_group_members.items():
        conscribo_group = conscribo_groups_by_name.get(group_name)
        if not conscribo_group:
            logging.info(f"Group not found in Conscribo: '{group_name}', skipping.")
            continue

        conscribo_member_ids = set(a["entityId"] for a in conscribo_group["members"])

        cognito_member_ids = set(a["conscribo_id"] for a in cognito_members)

        to_add = cognito_member_ids - conscribo_member_ids
        to_remove = conscribo_member_ids - cognito_member_ids

        if len(to_add) > 0:
            logging.info(
                f"ADD {','.join(sorted(to_add))} TO {group_name}"
            )

            if not dry_run:
                res = add_relations_to_group(
                    conscribo_group["id"],
                    list(to_add),
                )
                logging.debug("Response from Conscribo API:")
                logging.debug(increase_indent(json.dumps(res, indent=2)))

                logging.info(f"Added {len(to_add)} users to Conscribo group {group_name}")
                sleep(2)

        if len(to_remove) > 0:
            logging.info(
                f"REMOVE {','.join(sorted(to_remove))} FROM {group_name}"
            )

            if not dry_run:
                res = remove_relations_from_group(
                    conscribo_group["id"],
                    list(to_remove),
                )
                logging.debug("Response from Conscribo API:")
                logging.debug(increase_indent(json.dumps(res, indent=2)))

                logging.info(f"Removed {len(to_remove)} users from Conscribo group {group_name}")
                sleep(2)
        logging.info("")

if __name__ == "__main__":
    sync_cognito_to_conscribo_groups(dry_run=True)
