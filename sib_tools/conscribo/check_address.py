from time import sleep
import logging
import sys
import re
import requests
import os
import json
import hashlib

from . import auth
from .relations import list_relations_persoon, update_relation, list_relations_alumnus
from .groups import get_group_members
from . import groups
from .check_numbering import check_relation_number_correct
from dataclasses import dataclass
from .check_numbering import is_external_number
from .file_cache import file_cache, make_cache_key


@dataclass
class AddressOuput:
    postal_code: str
    street_names: list[str]
    place_names: list[str]
    addresses: list[dict]


def format_house_number(number, addition, house_letter, house_number):
    """
    Format house number with addition and house letter.

    Args:
        number: The base house number
        addition: Additional text (e.g., "BS" for "bis", followed by optional letter)
        house_letter: House letter (not used in current implementation)
        house_number: Fallback house number string

    Returns:
        Formatted house number string
    """
    if addition is not None:
        match = re.match(r"^(BS)?([A-Z]?)$", addition)

        if match is None:
            return house_number

        val = str(number)
        if match.group(1) is not None:
            val += " bis"

        if match.group(2) is not None and len(match.group(2)) > 0:
            val += f" {match.group(2)}"

        return val

    return house_number


def get_for_postal_code(postal_code) -> AddressOuput:
    """
    Get address information for a postal code from the Dutch PDOK API.

    Args:
        postal_code: Dutch postal code (postcode)

    Returns:
        AddressOuput containing place names, street names, and addresses
    """
    postal_code = postal_code.replace(" ", "")
    docs = []

    if len(postal_code) == 6:
        url = f"https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q={postal_code}&rows=100&df=postcode"
        cache_dir = os.path.expanduser("~/.sib_pdok_cache")
        cache_key = make_cache_key(url, postal_code=postal_code)
        with file_cache(cache_dir, cache_key) as cached:
            if cached is not None:
                data = cached
            else:
                try:
                    logging.debug(
                        f"Fetching postal code data for {postal_code} from PDOK API"
                    )
                    response = requests.get(url)
                    response.raise_for_status()
                    data = response.json()
                    with open(
                        os.path.join(cache_dir, cache_key), "w", encoding="utf-8"
                    ) as f:
                        json.dump(data, f)
                    sleep(1)  # Rate limiting
                except requests.exceptions.RequestException as e:
                    logging.error(f"Error fetching postal code data: {e}")
                    return AddressOuput(
                        postal_code=postal_code,
                        street_names=[],
                        place_names=[],
                        addresses=[],
                    )
            docs = data.get("response", {}).get("docs", [])

    # Filter for postal code information
    postal_code_infos = [doc for doc in docs if doc.get("type") == "postcode"]
    place_names = sorted(
        list(
            set(
                info.get("woonplaatsnaam", "")
                for info in postal_code_infos
                if info.get("woonplaatsnaam")
            )
        )
    )
    street_names = sorted(
        list(
            set(
                info.get("straatnaam", "")
                for info in postal_code_infos
                if info.get("straatnaam")
            )
        )
    )

    # Filter for address information
    addresses = [doc for doc in docs if doc.get("type") == "adres"]

    # Format addresses
    formatted_addresses = []
    for address in addresses:
        formatted_addresses.append(
            {
                "number": format_house_number(
                    address.get("huisnummer"),
                    address.get("huisnummertoevoeging"),
                    address.get("huisletter"),
                    address.get("huis_nlt"),
                ),
                "house_number": address.get("huis_nlt"),
                "place_name": address.get("woonplaatsnaam"),
                "street_name": address.get("straatnaam"),
                "rdf": address.get("rdf_seealso"),
                "details": address.get("rdf_seealso"),
            }
        )

    return AddressOuput(
        postal_code=postal_code,
        street_names=street_names,
        place_names=place_names,
        addresses=formatted_addresses,
    )


def check_address(
    relation, report_if_empty=True, report_if_correct=True, report_if_external=False,
    relation_type="Relation"
):
    selector = relation["other"]["selector"]

    if is_external_number(relation["conscribo_id"]):
        if report_if_external:
            logging.debug(
                f"Skipping address check for external relation: {selector} ({relation['conscribo_id']})"
            )
        return True

    postal_code = relation.get("postal_code")
    if postal_code is None:
        if report_if_empty:
            logging.warning(
                f"\x1b[33mProblem found: \x1b[0m {relation_type} \x1b[93m'{selector}'\x1b[0m has no postal code."
            )
        return True

    house_number = relation.get("house_number_full")
    if house_number is None:
        house_number = relation.get("house_number_decimal")

        if house_number is None:
            if report_if_empty:
                logging.warning(
                    f"\x1b[33mProblem found: \x1b[0m {relation_type} \x1b[93m'{selector}'\x1b[0m has no house number."
                )
            return True
        house_number += relation.get("house_number_addition", "")

    street_name = relation.get("street")
    place_name = relation.get("place")

    address_output = get_for_postal_code(postal_code)

    if street_name not in address_output.street_names:
        logging.warning(
            f"\x1b[33mProblem found: \x1b[0m {relation_type} \x1b[93m'{selector}'\x1b[0m has street name '{street_name}', "
            f"expected one of the following based on postal code '{postal_code}': "
        )
        for street in address_output.street_names or ["--no street names found--"]:
            logging.warning(f"    - {street}")
        return True

    if place_name not in address_output.place_names:
        logging.warning(
            f"\x1b[33mProblem found: \x1b[0m {relation_type} \x1b[93m'{selector}'\x1b[0m has place name '{place_name}', "
            f"expected one of the following based on postal code '{postal_code}': "
        )
        for place in address_output.place_names or ["--no place names found--"]:
            logging.warning(f"    - {place}")
        return True

    valid_house_numbers = [
        addr["number"]
        for addr in address_output.addresses
        if addr["street_name"] == street_name
    ]

    if house_number not in valid_house_numbers:
        logging.warning(
            f"\x1b[33mProblem found: \x1b[0m {relation_type} \x1b[93m'{relation['other']['selector']}'\x1b[0m has house number '{house_number}', "
            f"expected one of the following based on postal code '{postal_code}' and street name '{street_name}': "
        )
        logging.warning(f"   - {', '.join(valid_house_numbers)}")
        # for addr in address_output.addresses:
        #     if addr["street_name"] == street_name:
        #         logging.warning(f"    - {addr['number']} ({addr['place_name']})")
        return True

    if report_if_correct:
        logging.info(f"\x1b[32mAddress for '{selector}' is correct \x1b[0m")

    # logging.debug(f"Address output for {selector}: {address_output}")


def check_addresses(include_alumni=True, include_members=True):
    logging.basicConfig(
        filename="conscribo_check_basic.log",
        level=logging.DEBUG,
        format="[%(asctime)s] %(levelname)s: %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    logging.info("\x1b[94mPreparing...\x1b[0m")

    auth.do_auth()

    if include_members:
        personen = list_relations_persoon()
        logging.info(f"Fetched {len(personen)} persons from Conscribo.")
        logging.info("")
    else:
        personen = []

    logging.info("\x1b[94mPreparation done.\x1b[0m\n")

    logging.info("\x1b[94mChecking addresses...\x1b[0m")
    logging.info("  To not overuse the API, this will take a while.")
    if include_members:
        logging.info("Checking for members...")
        for relation in personen:
            check_address(
                relation,
                report_if_empty=True,
                report_if_correct=True,
                report_if_external=False,
                relation_type="Member",
            )
        logging.info("")
    if include_alumni:
        logging.info("Checking for alumni...")
        alumni = list_relations_alumnus()
        logging.info(f"Fetched {len(alumni)} alumni from Conscribo.")    
        for relation in alumni:
            check_address(
                relation,
                report_if_empty=True,
                report_if_correct=True,
                report_if_external=True,
                relation_type="Alumnus",
            )
    logging.info("\x1b[94mAddress check done.\x1b[0m\n")
