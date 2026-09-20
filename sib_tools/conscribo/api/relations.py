from typing import Any

from sib_tools.conscribo.auth import conscribo_delete, conscribo_get, conscribo_patch, conscribo_post
from sib_tools.conscribo.types import (
    ConscriboArchiveRelationsRequest,
    ConscriboChangedEntityIdsResponse,
    ConscriboCreateRelationRequest,
    ConscriboCreateRelationResponse,
    ConscriboDeleteRelationResponse,
    ConscriboEntityFiltersResponse,
    ConscriboEntityGroupsResponse,
    ConscriboEntityTypesResponse,
    ConscriboFieldDefinitionsResponse,
    ConscriboGroupMembersOperationRequest,
    ConscriboGroupMembersOperationResponse,
    ConscriboRelationFilterRequest,
    ConscriboRelationFiltersResponse,
    ConscriboUpdateRelationRequest,
)


def create_relation(payload: ConscriboCreateRelationRequest | dict[str, Any]) -> ConscriboCreateRelationResponse:
    """POST /relations/"""
    return conscribo_post("/relations/", json=payload, return_type=ConscriboCreateRelationResponse)


def update_relation(
    relation_nr: str,
    payload: ConscriboUpdateRelationRequest | dict[str, Any],
) -> ConscriboCreateRelationResponse:
    """PATCH /relations/{relationNr}"""
    return conscribo_patch(
        f"/relations/{relation_nr}",
        json=payload,
        return_type=ConscriboCreateRelationResponse,
    )


def delete_relation(relation_nr: str) -> ConscriboDeleteRelationResponse:
    """DELETE /relations/{relationNr}"""
    return conscribo_delete(f"/relations/{relation_nr}", params=None, return_type=ConscriboDeleteRelationResponse)


def archive_relations(
    payload: ConscriboArchiveRelationsRequest | dict[str, Any],
) -> ConscriboGroupMembersOperationResponse:
    """POST /relations/archive/"""
    return conscribo_post(
        "/relations/archive/",
        json=payload,
        return_type=ConscriboGroupMembersOperationResponse,
    )


def get_entity_types() -> ConscriboEntityTypesResponse:
    """GET /relations/entityTypes/"""
    return conscribo_get("/relations/entityTypes/", return_type=ConscriboEntityTypesResponse)


def get_field_definitions(entity_type: str) -> ConscriboFieldDefinitionsResponse:
    """GET /relations/fieldDefinitions/{entityType}"""
    return conscribo_get(
        f"/relations/fieldDefinitions/{entity_type}",
        return_type=ConscriboFieldDefinitionsResponse,
    )


def filter_relations(payload: ConscriboRelationFilterRequest | dict[str, Any]) -> ConscriboRelationFiltersResponse:
    """POST /relations/filters/"""
    return conscribo_post(
        "/relations/filters/",
        json=payload,
        return_type=ConscriboRelationFiltersResponse,
    )


def filter_entities(payload: dict[str, Any]) -> ConscriboEntityFiltersResponse:
    """POST /relations/entities/filters/"""
    return conscribo_post("/relations/entities/filters/", json=payload, return_type=ConscriboEntityFiltersResponse)


def get_changed_entity_ids(timestamp: int) -> ConscriboChangedEntityIdsResponse:
    """GET /relations/entities/changedIds/?timestamp=..."""
    return conscribo_get(
        f"/relations/entities/changedIds/?timestamp={timestamp}",
        return_type=ConscriboChangedEntityIdsResponse,
    )


def get_entity_groups(group_id: int | str | None = None) -> ConscriboEntityGroupsResponse:
    """GET /relations/groups/{groupId}/ or GET /relations/groups/"""
    if group_id is None:
        return conscribo_get("/relations/groups/", return_type=ConscriboEntityGroupsResponse)
    return conscribo_get(f"/relations/groups/{group_id}/", return_type=ConscriboEntityGroupsResponse)


def add_group_members(
    group_id: int | str,
    payload: ConscriboGroupMembersOperationRequest | dict[str, Any],
) -> ConscriboGroupMembersOperationResponse:
    """POST /relations/groups/{groupId}/members/"""
    return conscribo_post(
        f"/relations/groups/{group_id}/members/",
        json=payload,
        return_type=ConscriboGroupMembersOperationResponse,
    )


def remove_group_members(group_id: int | str, relation_nrs: list[str]) -> ConscriboGroupMembersOperationResponse:
    """DELETE /relations/groups/{groupId}/members/?relationNrs=..."""
    params = {"relationNrs": ",".join(relation_nrs)}
    return conscribo_delete(
        f"/relations/groups/{group_id}/members/",
        params=params,
        return_type=ConscriboGroupMembersOperationResponse,
    )
