from typing import Any

from sib_tools.conscribo.auth import conscribo_get, conscribo_patch, conscribo_post
from sib_tools.conscribo.types import (
    ConscriboAccountsResponse,
    ConscriboDeclarationMessageRequest,
    ConscriboDeclarationMessageResponse,
    ConscriboReplaceTransactionResponse,
    ConscriboTransaction,
    ConscriboTransactionFilterRequest,
    ConscriboTransactionsResponse,
    ConscriboVatCodesResponse,
)


def get_financial_accounts(date: str) -> ConscriboAccountsResponse:
    """GET /financial/accounts/?date=YYYY-MM-DD"""
    return conscribo_get(f"/financial/accounts/?date={date}", return_type=ConscriboAccountsResponse)


def add_financial_transaction(payload: ConscriboTransaction) -> ConscriboReplaceTransactionResponse:
    """POST /financial/transactions/"""
    return conscribo_post(
        "/financial/transactions/",
        json=payload,
        return_type=ConscriboReplaceTransactionResponse,
    )


def get_financial_transactions_by_ids(ids: list[int]) -> ConscriboTransactionsResponse:
    """GET /financial/transactions/?ids=1,2,3"""
    ids_param = ",".join(str(item) for item in ids)
    return conscribo_get(f"/financial/transactions/?ids={ids_param}", return_type=ConscriboTransactionsResponse)


def update_financial_transaction(
    transaction_id: int | str,
    payload: ConscriboTransaction,
) -> ConscriboReplaceTransactionResponse:
    """PATCH /financial/transactions/{id}"""
    return conscribo_patch(
        f"/financial/transactions/{transaction_id}",
        json=payload,
        return_type=ConscriboReplaceTransactionResponse,
    )


def filter_financial_transactions(
    payload: ConscriboTransactionFilterRequest | dict[str, Any],
) -> ConscriboTransactionsResponse:
    """POST /financial/transactions/filters/"""
    return conscribo_post(
        "/financial/transactions/filters/",
        json=payload,
        return_type=ConscriboTransactionsResponse,
    )


def get_vat_codes(date: str) -> ConscriboVatCodesResponse:
    """GET /financial/vatcodes/?date=YYYY-MM-DD"""
    return conscribo_get(f"/financial/vatcodes/?date={date}", return_type=ConscriboVatCodesResponse)


def add_declaration_message(
    payload: ConscriboDeclarationMessageRequest | dict[str, Any],
) -> ConscriboDeclarationMessageResponse:
    """POST /financial/declarationmessage/"""
    return conscribo_post(
        "/financial/declarationmessage/",
        json=payload,
        return_type=ConscriboDeclarationMessageResponse,
    )
