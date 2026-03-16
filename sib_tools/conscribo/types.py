from typing import Any, NotRequired, TypedDict


# ---------------------------------------------------------------------------
# Common response structures
# ---------------------------------------------------------------------------


class ConscriboUserMessage(TypedDict):
    message: str
    code: str
    hint: NotRequired[str]


class ConscriboResponseMessages(TypedDict):
    error: list[ConscriboUserMessage]
    warning: list[ConscriboUserMessage]
    info: list[ConscriboUserMessage]


# ---------------------------------------------------------------------------
# Sessions  (/sessions/)
# ---------------------------------------------------------------------------


class ConscriboSessionResponse(TypedDict):
    sessionId: str
    userDisplayName: str
    status: int
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboSessionStatusResponse(TypedDict):
    secsToLogout: int
    status: int
    responseMessages: NotRequired[ConscriboResponseMessages]


# ---------------------------------------------------------------------------
# Financial transactions  (/financial/transactions/filters/)
# ---------------------------------------------------------------------------


class ConscriboTransactionRow(TypedDict, total=False):
    accountNr: str
    amount: float
    side: str  # "credit" or "debet"
    reference: str
    description: str
    relationNr: str
    vatCode: str
    vatAmount: float


class ConscriboTransaction(TypedDict, total=False):
    transactionId: int
    date: str  # YYYY-MM-DD
    description: str
    transactionNr: str
    transactionRows: list[ConscriboTransactionRow]


class ConscriboTransactionsResponse(TypedDict):
    transactions: list[ConscriboTransaction]
    nrTransactions: int | str
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


# ---------------------------------------------------------------------------
# Financial accounts  (/financial/accounts/)
# ---------------------------------------------------------------------------


class ConscriboAccount(TypedDict, total=False):
    accountNr: str
    accountName: str
    type: str      # "balance" or "result"
    usage: str     # "generic", "transactional", "financial", "bank", "savings", "vat"
    usedForCredit: bool
    usedForDebit: bool
    parent: str    # accountNr of the parent account; absent on root accounts


class ConscriboAccountsResponse(TypedDict):
    accounts: list[ConscriboAccount]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


# ---------------------------------------------------------------------------
# VAT codes  (/financial/vatcodes/)
# ---------------------------------------------------------------------------


class ConscriboVatCode(TypedDict):
    code: str
    name: str
    percentage: float
    isReverseChargeGroup: bool
    sectionToPay: str
    sectionToReceive: str
    sectionToPayReverseCharge: NotRequired[str]


class ConscriboVatCodesResponse(TypedDict):
    vatCodes: list[ConscriboVatCode]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


# ---------------------------------------------------------------------------
# Entity types  (/relations/entityTypes/)
# ---------------------------------------------------------------------------


class ConscriboEntityType(TypedDict):
    typeName: str
    langDeterminer: str
    langSingular: str
    langPlural: str


class ConscriboEntityTypesResponse(TypedDict):
    entityTypes: list[ConscriboEntityType]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


# ---------------------------------------------------------------------------
# Field definitions  (/relations/fieldDefinitions/{entityType})
# ---------------------------------------------------------------------------


class ConscriboFieldDefinition(TypedDict, total=False):
    fieldName: str           # Required identifier
    entityType: str          # Required entity type
    label: str               # Required user-friendly name
    description: str
    type: str                # text, textarea, number, date, amount, checkbox,
                             # multicheckbox, enum, mailadres, account, file, folder
    required: int            # 0 or 1
    readOnly: int            # 0 or 1
    possibleValues: list[str]
    sharedFieldName: str
    category: str
    positionInCategory: int


class ConscriboFieldDefinitionsResponse(TypedDict):
    fields: list[ConscriboFieldDefinition]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


# ---------------------------------------------------------------------------
# Relations  (/relations/filters/, /relations/)
# ---------------------------------------------------------------------------

# Individual relation objects contain a fixed set of base fields plus an
# arbitrary number of dynamic fields whose names and types depend on the
# entity type's field definitions. We therefore represent them as plain
# dict[str, Any] where the caller can use ConscriboFieldDefinition metadata
# to interpret the values.

ConscriboRelation = dict[str, Any]


class ConscriboRelationFiltersResponse(TypedDict):
    resultCount: int
    relations: dict[str, ConscriboRelation]  # keyed by relation number
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboCreateRelationResponse(TypedDict):
    code: str  # Assigned relation number (Conscribo ID)
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


# ---------------------------------------------------------------------------
# Entity groups  (/relations/groups/)
# ---------------------------------------------------------------------------


class ConscriboEntityGroupMember(TypedDict):
    entityId: str
    entityType: NotRequired[str]


class ConscriboEntityGroup(TypedDict):
    id: str
    name: str
    type: NotRequired[str]      # "universal" or "archive"
    parentId: NotRequired[str]  # "root" or parent group number
    members: NotRequired[list[ConscriboEntityGroupMember]]


class ConscriboEntityGroupsResponse(TypedDict):
    entityGroups: list[ConscriboEntityGroup]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboGroupMembersOperationResponse(TypedDict):
    numSuccess: int
    failed: dict[str, str]   # relationNr -> error message
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]
