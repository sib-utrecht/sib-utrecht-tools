from typing import Any

from sib_tools.conscribo.auth import conscribo_post
from sib_tools.conscribo.types import (
    ConscriboInvoiceFilterRequest,
    ConscriboInvoicePostRequest,
    ConscriboInvoicesResponse,
    ConscriboPostInvoiceResponse,
)


def add_invoice(payload: ConscriboInvoicePostRequest | dict[str, Any]) -> ConscriboPostInvoiceResponse:
    """POST /financial/invoices/"""
    return conscribo_post("/financial/invoices/", json=payload, return_type=ConscriboPostInvoiceResponse)


def filter_invoices(payload: ConscriboInvoiceFilterRequest | dict[str, Any]) -> ConscriboInvoicesResponse:
    """POST /financial/invoices/filters/"""
    return conscribo_post("/financial/invoices/filters/", json=payload, return_type=ConscriboInvoicesResponse)
