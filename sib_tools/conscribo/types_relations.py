from typing import Any, Literal, NotRequired, Required, TypeAlias, TypedDict

from .types_common import ConscriboBankAccountField, ConscriboFileField, ConscriboResponseMessages


class ConscriboEntityType(TypedDict):
    typeName: str
    langDeterminer: str
    langSingular: str
    langPlural: str


class ConscriboEntityTypesResponse(TypedDict):
    entityTypes: list[ConscriboEntityType]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboFieldDefinition(TypedDict, total=False):
    fieldName: Required[str]
    entityType: Required[str]
    label: Required[str]
    description: str
    type: str
    required: int
    readOnly: int
    possibleValues: list[str]
    sharedFieldName: str
    category: str
    positionInCategory: int


class ConscriboFieldDefinitionsResponse(TypedDict):
    fields: list[ConscriboFieldDefinition]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


ConscriboRelationFieldValue: TypeAlias = (
    str
    | float
    | int
    | bool
    | None
    | dict[str, Any]
    | list[Any]
    | ConscriboFileField
    | ConscriboBankAccountField
)

ConscriboRelation = dict[str, ConscriboRelationFieldValue]
ConscriboEntity = dict[str, ConscriboRelationFieldValue]


class ConscriboFilterDateValue(TypedDict, total=False):
    start: str
    stop: str | None


class ConscriboFilterString(TypedDict):
    fieldName: str
    operator: Literal["=", "~", "!~", "|=", "+", "-"]
    value: str


class ConscriboFilterNumber(TypedDict):
    fieldName: str
    operator: Literal["="]
    value: str


class ConscriboFilterDate(TypedDict):
    fieldName: str
    operator: Literal["><", ">=", "<="]
    value: ConscriboFilterDateValue


class ConscriboFilterCheckbox(TypedDict):
    fieldName: str
    operator: Literal["="]
    value: int


class ConscriboFilterMultiCheckbox(TypedDict):
    fieldName: str
    operator: Literal["=", "in", "all", "<>"]
    value: int


ConscriboRelationFilter: TypeAlias = (
    ConscriboFilterString
    | ConscriboFilterNumber
    | ConscriboFilterDate
    | ConscriboFilterCheckbox
    | ConscriboFilterMultiCheckbox
)


class ConscriboRelationFilterRequest(TypedDict, total=False):
    entityType: str
    requestedFields: list[str]
    filters: list[ConscriboRelationFilter | dict[str, Any]]
    offset: int
    limit: int


class ConscriboRelationFiltersResponse(TypedDict):
    resultCount: int
    relations: dict[str, ConscriboRelation]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboEntityFiltersResponse(TypedDict):
    resultCount: int
    entities: dict[str, ConscriboEntity]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboChangedEntityIdsResponse(TypedDict):
    ids: list[str]
    entityIds: NotRequired[list[str]]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboCreateRelationRequest(TypedDict):
    entityType: str
    fields: dict[str, Any]


class ConscriboCreateRelationResponse(TypedDict):
    code: str
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboUpdateRelationRequest(TypedDict):
    fields: dict[str, Any]


class ConscriboDeleteRelationResponse(TypedDict, total=False):
    deleted: bool
    status: int
    responseMessages: ConscriboResponseMessages


class ConscriboEntityGroupMember(TypedDict):
    entityId: str
    entityType: NotRequired[str]


class ConscriboEntityGroup(TypedDict):
    id: str
    name: str
    type: NotRequired[str]
    parentId: NotRequired[str]
    members: NotRequired[list[ConscriboEntityGroupMember]]


class ConscriboEntityGroupsResponse(TypedDict):
    entityGroups: list[ConscriboEntityGroup]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboGroupMembersOperationRequest(TypedDict):
    relationIds: list[str]


class ConscriboGroupMembersOperationResponse(TypedDict):
    numSuccess: int
    failed: dict[str, str]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboArchiveRelationsRequest(TypedDict, total=False):
    relationIds: list[str]
    archiveGroupId: str
    renameCodeToArchiveCode: bool
