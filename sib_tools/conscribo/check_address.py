from time import sleep
import logging
import re
import requests
import os
import json
from typing import TYPE_CHECKING, Callable, Mapping, TypedDict, cast

from .relations import list_relations_persoon, list_relations_alumnus
from dataclasses import dataclass
from .check_numbering import is_external_number as _is_external_number  # type: ignore
from .file_cache import file_cache, make_cache_key

if TYPE_CHECKING:
    from logging import Logger


@dataclass
class AddressOutput:
    postal_code: str
    street_names: list[str]
    place_names: list[str]
    addresses: list["AddressRecord"]


# Backward compatibility for old class name.
AddressOuput = AddressOutput


class AddressRecord(TypedDict):
    number: str
    house_number: str
    place_name: str
    street_name: str
    rdf: str
    details: str


is_external_number: Callable[[object], bool] = cast(
    Callable[[object], bool], _is_external_number
)


def _as_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if value is None:
        return None
    return str(value)


def format_house_number(
    number: object,
    addition: str | None,
    house_letter: str | None,
    house_number: str | None,
) -> str:
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
    _ = house_letter  # currently unused

    if addition is not None:
        match = re.match(r"^(BS)?([A-Z]?)$", addition)

        if match is None:
            return house_number or ""

        val = str(number)
        if match.group(1) is not None:
            val += " bis"

        if match.group(2) is not None and len(match.group(2)) > 0:
            val += f" {match.group(2)}"

        return val

    return house_number or ""


def get_for_postal_code(postal_code: str) -> AddressOutput:
    """
    Get address information for a postal code from the Dutch PDOK API.

    Args:
        postal_code: Dutch postal code (postcode)

    Returns:
        AddressOuput containing place names, street names, and addresses
    """
    postal_code = postal_code.replace(" ", "")
    docs: list[dict[str, object]] = []

    if len(postal_code) == 6:
        url = f"https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q={postal_code}&rows=100&df=postcode"
        cache_dir = os.path.expanduser("~/.sib_pdok_cache")
        cache_key = make_cache_key(url, postal_code=postal_code)
        with file_cache(cache_dir, cache_key) as cached:
            data: dict[str, object]
            if cached is not None:
                if isinstance(cached, dict):
                    data = cast(dict[str, object], cached)
                else:
                    data = {}
            else:
                try:
                    logging.debug(
                        f"Fetching postal code data for {postal_code} from PDOK API"
                    )
                    response = requests.get(url)
                    response.raise_for_status()
                    response_json = response.json()
                    if isinstance(response_json, dict):
                        data = cast(dict[str, object], response_json)
                    else:
                        data = {}
                    with open(
                        os.path.join(cache_dir, cache_key), "w", encoding="utf-8"
                    ) as f:
                        json.dump(data, f)
                    sleep(1)  # Rate limiting
                except requests.exceptions.RequestException as e:
                    logging.error(f"Error fetching postal code data: {e}")
                    return AddressOutput(
                        postal_code=postal_code,
                        street_names=[],
                        place_names=[],
                        addresses=[],
                    )
            response_data = data.get("response")
            if isinstance(response_data, dict):
                response_dict = cast(dict[str, object], response_data)
                raw_docs = response_dict.get("docs")
                if isinstance(raw_docs, list):
                    docs = [
                        cast(dict[str, object], raw_doc)
                        for raw_doc in cast(list[object], raw_docs)
                        if isinstance(raw_doc, dict)
                    ]

    # Filter for postal code information
    postal_code_infos = [doc for doc in docs if doc.get("type") == "postcode"]
    place_names = sorted(
        list(
            set(
                value
                for info in postal_code_infos
                if (value := _as_str(info.get("woonplaatsnaam")))
            )
        )
    )
    street_names = sorted(
        list(
            set(
                value
                for info in postal_code_infos
                if (value := _as_str(info.get("straatnaam")))
            )
        )
    )

    # Filter for address information
    addresses = [doc for doc in docs if doc.get("type") == "adres"]

    # Format addresses
    formatted_addresses: list[AddressRecord] = []
    for address in addresses:
        formatted_addresses.append(
            {
                "number": format_house_number(
                    address.get("huisnummer"),
                    _as_str(address.get("huisnummertoevoeging")),
                    _as_str(address.get("huisletter")),
                    _as_str(address.get("huis_nlt")),
                ),
                "house_number": _as_str(address.get("huis_nlt")) or "",
                "place_name": _as_str(address.get("woonplaatsnaam")) or "",
                "street_name": _as_str(address.get("straatnaam")) or "",
                "rdf": _as_str(address.get("rdf_seealso")) or "",
                "details": _as_str(address.get("rdf_seealso")) or "",
            }
        )

    return AddressOutput(
        postal_code=postal_code,
        street_names=street_names,
        place_names=place_names,
        addresses=formatted_addresses,
    )

def color_selector(selector: str | None) -> str:
    """
    Colorize the selector for better visibility in logs.

    Args:
        selector: The selector string to colorize

    Returns:
        Colorized selector string
    """
    return f"\x1b[93m{selector}\x1b[0m" if selector else "No selector"

def color_fix_suggestion(suggestion: str | None) -> str:
    """
    Colorize the fix suggestion for better visibility in logs.

    Args:
        suggestion: The fix suggestion message to colorize

    Returns:
        Colorized fix suggestion message
    """
    return f"\x1b[32m{suggestion}\x1b[0m" if suggestion else "No fix suggestion"

def color_wrong_value(value: str | None) -> str:
    """
    Colorize the wrong value for better visibility in logs.

    Args:
        value: The value to colorize

    Returns:
        Colorized value string
    """
    return f"\x1b[31m{value or 'missing'}\x1b[0m"

def check_address(
    relation: Mapping[str, object],
    logger: "Logger",
    report_if_empty: bool = True,
    report_if_correct: bool = True,
    report_if_external: bool = False,
    relation_type: str = "Relation",
) -> bool:
    _ = relation_type  # reserved for future use
    selector = "Unknown selector"
    other = relation.get("other")
    if isinstance(other, dict):
        other_dict = cast(dict[str, object], other)
        maybe_selector = other_dict.get("selector")
        if isinstance(maybe_selector, str):
            selector = maybe_selector
    selector_colored = color_selector(selector)

    def format_problem_found(problem: str) -> str:
        return f"\x1b[31mProblem found: {problem}\x1b[0m\n"

    conscribo_id = relation.get("conscribo_id")
    if conscribo_id is not None and bool(is_external_number(conscribo_id)):
        if report_if_external:
            logger.debug(
                f"Skipping address check for external relation: {selector} ({conscribo_id})"
            )
        return True
    street_name = _as_str(relation.get("street"))
    place_name = _as_str(relation.get("place"))
    missing_value = color_wrong_value("missing")
    postal_code = _as_str(relation.get("postal_code"))
    house_number = _as_str(relation.get("house_number_full"))
    if house_number is None:
        house_number = _as_str(relation.get("house_number_decimal"))
        if house_number is None:
            if report_if_empty:
                msg = (
                    format_problem_found("Missing house number.") +
                    f"  Name: {selector_colored}\n"
                    f"  Street: {street_name or '-'}\n"
                    f"  House number: {missing_value}\n"
                    f"  Postal code: {postal_code or '-'}\n"
                    f"  Place: {place_name or '-'}\n"
                )
                for line in msg.rstrip().split("\n"):
                    logger.warning(line)
            return True
        house_number += _as_str(relation.get("house_number_addition")) or ""
    if postal_code is None:
        if report_if_empty:
            msg = (
                format_problem_found("Missing postal code.") +
                f"  Name: {selector_colored}\n"
                f"  Street: {street_name or '-'}\n"
                f"  House number: {house_number or '-'}\n"
                f"  Postal code: {missing_value}\n"
                f"  Place: {place_name or '-'}\n"
            )
            for line in msg.rstrip().split("\n"):
                logger.warning(line)
        return True
    address_output = get_for_postal_code(postal_code)
    if street_name not in address_output.street_names:
        msg = (
            format_problem_found("Invalid street name.") +
            f"  Name: {selector_colored}\n"
            f"  Street: {color_wrong_value(street_name)}\n"
            f"  House number: {house_number or '-'}\n"
            f"  Postal code: {postal_code or '-'}\n"
            f"  Place: {place_name or '-'}\n"
            f"  Expected street name:"
        )
        for line in msg.rstrip().split("\n"):
            logger.warning(line)
        for street in address_output.street_names or ["--no street names found--"]:
            logger.warning(f"    - {color_fix_suggestion(street)}")
        logger.warning("")
        return True
    if place_name not in address_output.place_names:
        msg = (
            format_problem_found("Invalid place name.") +
            f"  Name: {selector_colored}\n"
            f"  Street: {street_name or '-'}\n"
            f"  House number: {house_number or '-'}\n"
            f"  Postal code: {postal_code or '-'}\n"
            f"  Place: {color_wrong_value(place_name)}\n"
            f"  Expected place name:"
        )
        for line in msg.rstrip().split("\n"):
            logger.warning(line)
        for place in address_output.place_names or ["--no place names found--"]:
            logger.warning(f"    - {color_fix_suggestion(place)}")
        logger.warning("")
        return True
    valid_house_numbers = [
        addr["number"]
        for addr in address_output.addresses
        if addr["street_name"] == street_name
    ]
    if house_number not in valid_house_numbers:
        msg = (
            format_problem_found("Invalid house number.") +
            f"  Name: {selector_colored}\n"
            f"  Street: {street_name or '-'}\n"
            f"  House number: {color_wrong_value(house_number)}\n"
            f"  Postal code: {postal_code or '-'}\n"
            f"  Place: {place_name or '-'}\n"
            f"  Expected house number:"
        )
        for line in msg.rstrip().split("\n"):
            logger.warning(line)
        logger.warning(f"    - {', '.join(color_fix_suggestion(num) for num in valid_house_numbers)}")
        logger.warning("")
        return True
    if report_if_correct:
        logger.info(
            f"\x1b[32mAddress for '{selector_colored}'\x1b[32m is correct\x1b[0m"
        )
        logger.info("")
    # logger.debug(f"Address output for {selector}: {address_output}")
    return False

def check_addresses(
    logger: "Logger", include_alumni: bool = True, include_members: bool = True
) -> None:
    logger.info("\x1b[94mPreparing...\x1b[0m")
    personen: list[Mapping[str, object]]
    if include_members:
        personen = cast(list[Mapping[str, object]], list_relations_persoon())
        logger.info(f"Fetched {len(personen)} persons from Conscribo.")
        logger.info("")
    else:
        personen = []
    logger.info("\x1b[94mPreparation done.\x1b[0m")
    logger.info("")
    logger.info("\x1b[94mChecking addresses...\x1b[0m")
    logger.info("  To not overuse the API, this will take a while.")
    if include_members:
        logger.info("Checking for members...")
        for relation in personen:
            check_address(
                relation,
                logger,
                report_if_empty=True,
                report_if_correct=True,
                report_if_external=False,
                relation_type="Member",
            )
        logger.info("")
    if include_alumni:
        logger.info("Checking for alumni...")
        alumni = cast(list[Mapping[str, object]], list_relations_alumnus())
        logger.info(f"Fetched {len(alumni)} alumni from Conscribo.")    
        for relation in alumni:
            check_address(
                relation,
                logger,
                report_if_empty=True,
                report_if_correct=True,
                report_if_external=True,
                relation_type="Alumnus",
            )
    logger.info("\x1b[94mAddress check done.\x1b[0m\n")
