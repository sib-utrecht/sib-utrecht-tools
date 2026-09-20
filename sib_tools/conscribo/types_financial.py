from typing import Any, NotRequired, TypedDict

from .types_common import ConscriboResponseMessages


class ConscriboAccount(TypedDict, total=False):
    accountNr: str
    accountName: str
    type: str
    usage: str
    usedForCredit: bool
    usedForDebit: bool
    parent: str


class ConscriboAccountsResponse(TypedDict):
    accounts: list[ConscriboAccount]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboTransactionRow(TypedDict, total=False):
    accountNr: str
    amount: float
    side: str
    reference: str
    description: str
    relationNr: str
    vatCode: str
    vatAmount: float


class ConscriboTransaction(TypedDict, total=False):
    transactionId: int
    date: str
    description: str
    transactionNr: str
    transactionRows: list[ConscriboTransactionRow]


class ConscriboTransactionFilters(TypedDict, total=False):
    dateStart: str
    dateEnd: str
    accounts: list[str]
    ids: list[int]


class ConscriboTransactionFilterRequest(TypedDict, total=False):
    requestedFields: list[str]
    filters: ConscriboTransactionFilters
    limit: int
    offset: int


class ConscriboTransactionsResponse(TypedDict):
    transactions: list[ConscriboTransaction]
    nrTransactions: int | str
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboReplaceTransactionResponse(TypedDict, total=False):
    transactionId: int
    transactionNr: str
    status: int
    responseMessages: ConscriboResponseMessages


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


class ConscriboDeclarationMessageRequest(TypedDict, total=False):
    relationNr: str
    subject: str
    message: str
    fileId: int


class ConscriboDeclarationMessageResponse(TypedDict, total=False):
    result: Any
    status: int
    responseMessages: ConscriboResponseMessages
