from typing import Any
from dataclasses import dataclass

from .auth import conscribo_post, conscribo_get, conscribo_delete
from .types import (
    ConscriboEntityGroup,
    ConscriboEntityGroupsResponse,
    ConscriboGroupMembersOperationResponse,
)

group_wil_geen_email_van_ons_ontvangen = 36

GroupId = int | str

entity_groups: list[ConscriboEntityGroup] | None = None

def get_group_members_cached(group_id: GroupId) -> set[str]:
    entity_groups = list_entity_groups()

    group = next((g for g in entity_groups if g["id"] == str(group_id)), None)
    if group is None:
        return get_group_members(group_id)

    return {a["entityId"] for a in group.get("members", [])}


def get_group_members(group_id: GroupId) -> set[str]:
    ans = conscribo_get(f"/relations/groups/{group_id}/", return_type=ConscriboEntityGroupsResponse)

    if len(ans["entityGroups"]) != 1:
        print(f"Error: {ans}")
        raise Exception("Unexpected number of entity groups")

    group = ans["entityGroups"][0]
    name = group["name"]

    print(f"{name} ({group['id']}) has {len(group.get('members', []))} members")

    return {a["entityId"] for a in group.get("members", [])}

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

def get_block_email_members() -> set[str]:
    return get_group_members(group_wil_geen_email_van_ons_ontvangen)

def list_entity_groups() -> list[ConscriboEntityGroup]:
    global entity_groups
    if entity_groups is None:
        ans = conscribo_get("/relations/groups/", return_type=ConscriboEntityGroupsResponse)
        entity_groups = ans["entityGroups"]

    assert entity_groups is not None
    return entity_groups

def list_entity_groups_by_name() -> dict[str, ConscriboEntityGroup]:
    """
    Returns a dictionary of entity groups indexed by their name.
    """
    return {
        group["name"]: group for group in list_entity_groups()
    }

def find_group_id_by_name(name: str) -> str | None:
    def normalize(name : str) -> str:
        return name.lower().replace(" ", "_").replace("-", "_")

    groups = {
        normalize(group["name"]): group for group in list_entity_groups()
    }

    group = groups.get(normalize(name))
    return group["id"] if group else None

def add_relations_to_group(
    group_id: GroupId,
    user_ids: list[str],
) -> ConscriboGroupMembersOperationResponse:
    return conscribo_post(
        f"/relations/groups/{group_id}/members/",
        json={"relationIds": user_ids},
        return_type=ConscriboGroupMembersOperationResponse,
    )


def remove_relations_from_group(
    group_id: GroupId,
    user_ids: list[str],
) -> ConscriboGroupMembersOperationResponse:
    return conscribo_delete(
        f"/relations/groups/{group_id}/members/",
        params={"relationIds": user_ids},
        return_type=ConscriboGroupMembersOperationResponse,
    )


def set_group_members(
    group_id: GroupId,
    canonical_members: list[dict[str, Any]],
    dry_run: bool = True
) -> None:
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
    desired_member_ids: set[str] = set()
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
