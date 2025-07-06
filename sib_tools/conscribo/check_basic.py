from time import sleep
import logging
import sys
import re
import requests

from . import auth
from .relations import list_relations_persoon, update_relation, list_relations_alumnus
from .groups import get_group_members
from . import groups
from .check_numbering import check_relation_number_correct
from dataclasses import dataclass
from .check_address import check_address
from .check_numbering import is_external_number

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


def check_relations_for_empty_fields(relations):
    members_per_empty_fields = {}

    for relation in relations:
        if is_external_number(relation["conscribo_id"]):
            continue

        empty_fields = check_relation_fields_nonempty(relation, report=False)

        for field in empty_fields:
            members_per_empty_fields.setdefault(field, []).append(
                relation["other"]["selector"]
            )

    logging.info("")
    for field, selectors in sorted(
        members_per_empty_fields.items(), key=lambda x: should_be_nonempty.index(x[0])
    ):
        logging.warning(f"\x1b[33mProblem found: \x1b[0m")
        logging.info(f"  Found {len(selectors)} members with empty '{field}':")
        for selector in selectors:
            logging.info(f"    - {selector}")
        logging.info("")


def check_relation_fields_nonempty(relation, report=True):
    empty_fields = [field for field in should_be_nonempty if not relation.get(field)]

    if report and len(empty_fields) > 0:
        logging.warning(f"\x1b[33mProblem found: \x1b[0m")
        logging.warning(
            f"  Member \x1b[93m'{relation['other']['selector']}'\x1b[0m has no {', '.join(empty_fields)}."
        )
        logging.warning("")

    return empty_fields


def check_basic():
    logging.basicConfig(
        filename="conscribo_check_basic.log",
        level=logging.DEBUG,
        format="[%(asctime)s] %(levelname)s: %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    logging.info("\x1b[94mPreparing...\x1b[0m")

    auth.do_auth()

    personen = list_relations_persoon()
    alumni = list_relations_alumnus()

    logging.info(f"Fetched {len(personen)} persons from Conscribo.")
    logging.info(f"Fetched {len(alumni)} alumni from Conscribo.")
    logging.info("")

    logging.info("\x1b[94mPreparation done.\x1b[0m\n")

    correct = 0
    wrong = 0

    personen_by_membership_end = {}

    check_relations_for_empty_fields(personen)

    for relation in personen:
        if relation["conscribo_id"] == "666":
            continue  # Skip the test user

        check_relation_number_correct(relation)

        if relation["membership_end"] is not None:
            personen_by_membership_end.setdefault(
                relation["membership_end"], []
            ).append(relation)

        selector = relation["other"]["selector"]

    logging.info("")
    for membership_end, entry_members in sorted(
        personen_by_membership_end.items(), key=lambda x: x[0]
    ):
        logging.info(f"\x1b[94mInfo:\x1b[0m")
        logging.info(
            f"  Found {len(entry_members)} members with membership end \x1b[94m{membership_end}\x1b[0m:"
        )
        for relation in entry_members:
            selector = relation["other"]["selector"]
            logging.info(f"    - {selector}")
        logging.info("")

    # logging.info("\x1b[94mChecking addresses...\x1b[0m")
    # logging.info("  To not overuse the API, this will take a while.")    
    # for relation in personen:
    #     check_address(relation, report_if_empty=True)
    # logging.info("\x1b[94mAddress check done.\x1b[0m\n")
    logging.info("To check addresses, run `sib-tools check conscribo-addresses`.")

    logging.info("")
    logging.info(
        f"Processed {len(personen)} members: {correct} correct, {wrong} wrong."
    )
    logging.info("")
