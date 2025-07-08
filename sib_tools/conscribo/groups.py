import keyring.credentials
import requests
import json
import keyring
from getpass import getpass

from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict
from . import auth
from .auth import conscribo_post, conscribo_get, conscribo_patch, conscribo_delete
from dataclasses import dataclass

group_wil_geen_email_van_ons_ontvangen = 36

entity_groups = None

def get_group_members_cached(group_id) -> set[str]:
    entity_groups = list_entity_groups()

    group = next((g for g in entity_groups if g["id"] == str(group_id)), None)
    if group is None:
        return get_group_members(group_id)

    return {a["entityId"] for a in group["members"]}


def get_group_members(group_id) -> set[str]:
    ans = conscribo_get(f"/relations/groups/{group_id}/")

    if len(ans["entityGroups"]) != 1:
        print(f"Error: {ans}")
        raise Exception("Unexpected number of entity groups")

    ans = ans["entityGroups"][0]
    name = ans["name"]

    print(f"{name} ({ans['id']}) has {len(ans['members'])} members")

    return {a["entityId"] for a in ans["members"]}

@dataclass
class Groups:
    donateurs: set[str]
    externen: set[str]
    overige_externen_voor_incassos: set[str]
    uitschrijving_aangevraagd: set[str]
    wil_geen_email_van_ons_ontvangen: set[str]


def get_groups() -> Groups:
    return Groups(
        donateurs=get_group_members_cached("14"),
        externen=get_group_members_cached("13"),
        overige_externen_voor_incassos=get_group_members_cached("19"),
        uitschrijving_aangevraagd=get_group_members_cached("7"),
        wil_geen_email_van_ons_ontvangen=get_group_members_cached("36"),
    )

def get_block_email_members():
    return get_group_members(group_wil_geen_email_van_ons_ontvangen)

def list_entity_groups():
    global entity_groups
    if entity_groups is None:
        entity_groups = conscribo_get(f"/relations/groups/")["entityGroups"]

    return entity_groups

def add_relations_to_group(
    group_id : int,
    user_ids : list[str],
):
    return conscribo_post(
        f"/relations/groups/{group_id}/members/",
        json={
            "relationIds": user_ids
        },
    )

def remove_relations_from_group(
    group_id : int,
    user_ids : list[str],
):
    return conscribo_delete(
        f"/relations/groups/{group_id}/members/",
        data={
            "relationIds": user_ids
        },
    )


