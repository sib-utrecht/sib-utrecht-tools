import boto3
from time import sleep
import json
import logging
import sys

from ..conscribo.conscribo_list_relations import list_relations_members
from ..conscribo.conscribo_list_groups import list_entity_groups
from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict
from ..cognito.cognito_list_users import (
    list_all_cognito_users,
    cognito_user_to_canonical,
    canonical_to_cognito_user,
    cognito_client,
    user_pool_id,
    cognito_list_groups,
    cognito_list_users_in_group,
)

logging.basicConfig(filename="cognito_sync.log", level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def sync_conscribo_to_cognito_groups(dry_run=True):
    cognito_groups = cognito_list_groups()
    print(f"Groups count: {len(cognito_groups)}")

    cognito_groups_by_name = {group["GroupName"]: group for group in cognito_groups}
    cognito_group_members = {
        group["GroupName"]: cognito_list_users_in_group(group["GroupName"])
        for group in cognito_groups
    }

    conscribo_groups = list_entity_groups()

    accounts_group = next(
        (a for a in conscribo_groups if a["name"] == "accounts"), None
    )

    if accounts_group is None:
        raise Exception(
            "Please create a Conscribo group called 'accounts', with "
            "subgroups for each member group you need on Cognito (like 'admins')"
        )
    
    subgroups = [
        a for a in conscribo_groups
        if a["parentId"] == accounts_group["id"]
    ]
    subgroups.sort(key=lambda x: x["name"])

    print(f"Found {len(subgroups)} subgroups on Conscribo:")
    for subgroup in subgroups:
        print(f"  - {subgroup['name']} ({subgroup['id']}) with {len(subgroup['members'])} members")

    print()
    print(f"Found {len(cognito_group_members)} groups on Cognito:")
    for name, members in sorted(cognito_group_members.items(), key=lambda x: x[0]):
        print(f"  - {name} with {len(members)} members")

