from typing import NotRequired, TypedDict

from .types_common import ConscriboResponseMessages


class ConscriboInvoicePostProductRow(TypedDict, total=False):
    productCode: str
    quantity: float
    description: str
    amountExclVat: float
    vatCode: str


class ConscriboInvoicePostFreeRow(TypedDict, total=False):
    accountNr: str
    quantity: float
    description: str
    amountExclVat: float
    vatCode: str
    vatAmount: float


class ConscriboInvoice(TypedDict, total=False):
    invoiceId: int
    invoiceNr: str
    state: dict[str, str | int | float | bool | None]
    relationNr: str
    transactionId: int
    invoiceDate: str
    invoiceExpiryDate: str
    amountExclVat: float
    amountVat: float
    openAmount: float
    openAmountMsg: str
    file: dict[str, str | int]
    paymentUrl: str
    invoiceRows: list[ConscriboInvoicePostProductRow | ConscriboInvoicePostFreeRow]


class ConscriboInvoicePostRequest(TypedDict, total=False):
    relationNr: str
    invoiceDate: str
    invoiceExpiryDate: str
    invoiceRows: list[ConscriboInvoicePostProductRow | ConscriboInvoicePostFreeRow]
    invoiceNr: str


class ConscriboInvoiceFilterRequest(TypedDict, total=False):
    filters: dict[str, object]
    requestedFields: list[str]
    offset: int
    limit: int


class ConscriboPostInvoiceResponse(TypedDict, total=False):
    invoiceId: int
    invoiceNr: str
    transactionId: int
    transactionNr: str
    status: int
    responseMessages: ConscriboResponseMessages


class ConscriboInvoicesResponse(TypedDict):
    invoices: list[ConscriboInvoice]
    resultCount: NotRequired[int]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]
