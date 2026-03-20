"""High-level Conscribo API handlers.

These modules provide endpoint-level wrappers for the full documented API
surface while leaving legacy helpers unchanged.
"""

from .files import download_file
from .financial import (
    add_declaration_message,
    add_financial_transaction,
    filter_financial_transactions,
    get_financial_accounts,
    get_financial_transactions_by_ids,
    get_vat_codes,
    update_financial_transaction,
)
from .invoices import add_invoice, filter_invoices
from .multi import execute_multi_request
from .relations import (
    add_group_members,
    archive_relations,
    create_relation,
    delete_relation,
    filter_entities,
    filter_relations,
    get_changed_entity_ids,
    get_entity_groups,
    get_entity_types,
    get_field_definitions,
    remove_group_members,
    update_relation,
)
from .sessions import get_session_information, start_session

__all__ = [
    "start_session",
    "get_session_information",
    "get_financial_accounts",
    "add_financial_transaction",
    "get_financial_transactions_by_ids",
    "update_financial_transaction",
    "filter_financial_transactions",
    "get_vat_codes",
    "add_declaration_message",
    "add_invoice",
    "filter_invoices",
    "create_relation",
    "update_relation",
    "delete_relation",
    "archive_relations",
    "get_entity_types",
    "get_field_definitions",
    "filter_relations",
    "filter_entities",
    "get_changed_entity_ids",
    "get_entity_groups",
    "add_group_members",
    "remove_group_members",
    "execute_multi_request",
    "download_file",
]
