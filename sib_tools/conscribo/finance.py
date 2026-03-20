from datetime import datetime, timedelta
from typing import Any

from .auth import conscribo_post, conscribo_get
from .types import ConscriboAccountsResponse, ConscriboTransactionsResponse


def list_conscribo_accounts(date: str | None = None) -> ConscriboAccountsResponse:
    """
    List Conscribo accounts for a given date.

    If date is None, it will list all accounts.
    """
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    return conscribo_get(f"/financial/accounts/?date={date}", return_type=ConscriboAccountsResponse)


def list_conscribo_transactions(
    start_date: str,
    end_date: str,
    account_id: str | None,
    limit: int | None = None,
    offset: int = 0,
) -> ConscriboTransactionsResponse:
    """
    List Conscribo transactions for a given date range and account ID.
    """

    filters: dict[str, Any] = {
        "dateStart": start_date,
        "dateEnd": end_date,
    }

    if account_id is not None:
        filters["accounts"] = [account_id]

    payload: dict[str, Any] = {
        "filters": filters,
        "offset": offset,
    }

    if limit is not None:
        payload["limit"] = limit

    return conscribo_post("/financial/transactions/filters/", json=payload, return_type=ConscriboTransactionsResponse)
