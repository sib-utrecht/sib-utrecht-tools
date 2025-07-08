from time import sleep
import logging
import sys
import re
import requests
from typing import TYPE_CHECKING

from . import auth
from .relations import list_relations_persoon, update_relation, list_relations_alumnus
from .groups import get_group_members
from . import groups
from .check_numbering import check_relation_number_correct
from dataclasses import dataclass
from .check_address import check_address
from .check_numbering import is_external_number

if TYPE_CHECKING:
    from logging import Logger

should_be_nonempty = [
    "conscribo_id",
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "date_of_birth",
    "postal_code",
    "place",
    "street",
    "iban",
    "bic",
    "house_number_decimal",
    "membership_start",
]


def check_relations_for_empty_fields(relations, logger: 'Logger'):
    members_per_empty_fields = {}

    for relation in relations:
        if is_external_number(relation["conscribo_id"]):
            continue

        empty_fields = check_relation_fields_nonempty(relation, logger, report=False)

        for field in empty_fields:
            members_per_empty_fields.setdefault(field, []).append(
                relation["other"]["selector"]
            )

    logger.info("")
    for field, selectors in sorted(
        members_per_empty_fields.items(), key=lambda x: should_be_nonempty.index(x[0])
    ):
        logger.warning(f"\x1b[33mProblem found: \x1b[0m")
        logger.info(f"  Found {len(selectors)} members with empty '{field}':")
        for selector in selectors:
            logger.info(f"    - {selector}")
        logger.info("")


def check_relation_fields_nonempty(relation, logger: 'Logger', report=True):
    empty_fields = [field for field in should_be_nonempty if not relation.get(field)]

    if report and len(empty_fields) > 0:
        logger.warning(f"\x1b[33mProblem found: \x1b[0m")
        logger.warning(
            f"  Member \x1b[93m'{relation['other']['selector']}'\x1b[0m has no {', '.join(empty_fields)}."
        )
        logger.warning("")

    return empty_fields


def check_basic(logger: 'Logger'):
    logger.info("\x1b[94mPreparing...\x1b[0m")

    personen = list_relations_persoon()
    alumni = list_relations_alumnus()

    logger.info(f"Fetched {len(personen)} persons from Conscribo.")
    logger.info(f"Fetched {len(alumni)} alumni from Conscribo.")
    logger.info("")

    logger.info("\x1b[94mPreparation done.\x1b[0m\n")

    correct = 0
    wrong = 0

    personen_by_membership_end = {}

    check_relations_for_empty_fields(personen, logger)

    for relation in personen:
        if relation["conscribo_id"] == "666":
            continue  # Skip the test user

        check_relation_number_correct(relation, logger)

        if relation["membership_end"] is not None:
            personen_by_membership_end.setdefault(
                relation["membership_end"], []
            ).append(relation)

        selector = relation["other"]["selector"]

    logger.info("")
    for membership_end, entry_members in sorted(
        personen_by_membership_end.items(), key=lambda x: x[0]
    ):
        logger.info(f"\x1b[94mInfo:\x1b[0m")
        logger.info(
            f"  Found {len(entry_members)} members with membership end \x1b[94m{membership_end}\x1b[0m:"
        )
        for relation in entry_members:
            selector = relation["other"]["selector"]
            logger.info(f"    - {selector}")
        logger.info("")

    logger.info("To check addresses, run `sib-tools check conscribo-addresses`.")

    logger.info("")
