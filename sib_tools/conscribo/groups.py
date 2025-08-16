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

def list_entity_groups_by_name():
    """
    Returns a dictionary of entity groups indexed by their name.
    """
    return {
        group["name"]: group for group in list_entity_groups()
    }

def find_group_id_by_name(name: str) -> int | None:
    def normalize(name : str) -> str:
        return name.lower().replace(" ", "_").replace("-", "_")
    
    groups = {
        normalize(group["name"]): group for group in list_entity_groups()
    }

    group = groups.get(normalize(name))
    return group["id"] if group else None

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


def set_group_members(
    group_id: int,
    canonical_members: list[dict],
    dry_run: bool = True
):
    """
    Set the members of a Conscribo group based on a list of canonical members.
    
    Args:
        group_id: The ID of the Conscribo group
        canonical_members: List of canonical member dictionaries
        dry_run: If True, only show what would be changed without making actual changes
    
    This function will:
    1. Get the current group members
    2. Extract conscribo_ids from the canonical members
    3. Add missing members to the group
    4. Remove members that shouldn't be in the group
    """
    print(f"Setting members for group {group_id}")
    
    # Get current group members
    current_members = get_group_members_cached(group_id)
    print(f"Current group has {len(current_members)} members")
    
    # Extract conscribo_ids from canonical members
    desired_member_ids = set()
    for member in canonical_members:
        conscribo_id = member.get("conscribo_id")
        if conscribo_id:
            desired_member_ids.add(str(conscribo_id))
    
    print(f"Target group should have {len(desired_member_ids)} members")
    
    # Determine what changes need to be made
    members_to_add = desired_member_ids - current_members
    members_to_remove = current_members - desired_member_ids
    
    print(f"Need to add {len(members_to_add)} members")
    print(f"Need to remove {len(members_to_remove)} members")

    print(f"Adding members: {list(members_to_add)}")
    print(f"Removing members: {list(members_to_remove)}")
    
    if dry_run:
        print("DRY RUN MODE - No actual changes will be made")
        if members_to_add:
            print(f"Would add members: {list(members_to_add)}")
        if members_to_remove:
            print(f"Would remove members: {list(members_to_remove)}")
        return
    
    # Add missing members
    if members_to_add:
        print(f"Adding {len(members_to_add)} members to group {group_id}")
        add_relations_to_group(group_id, list(members_to_add))
    
    # Remove extra members
    if members_to_remove:
        print(f"Removing {len(members_to_remove)} members from group {group_id}")
        remove_relations_from_group(group_id, list(members_to_remove))
    
    if not members_to_add and not members_to_remove:
        print("Group membership is already up to date")
    else:
        print(f"Group {group_id} membership updated successfully")


