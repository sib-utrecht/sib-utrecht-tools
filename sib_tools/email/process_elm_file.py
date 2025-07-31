import logging
import sys
import json

from sib_tools.conscribo.relations import create_relation_member
from sib_tools.email.forms_extract_mail import form_to_canonical

from sib_tools.email.forms_extract_mail import (
    extract_fields_from_mail,
    extract_fields_from_mail_message,
    form_to_canonical,
)
from .dkim_verify import DKIMDetailsVerified, verify_dkim_signature

logger = logging.getLogger("incoming_email.log")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("sib_tools_incoming_email.log")
file_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
)
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
# stream_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
logger.addHandler(stream_handler)

def process_registration_email(dkim_result : DKIMDetailsVerified):
    fields = extract_fields_from_mail_message(dkim_result.email)
    canonical = form_to_canonical(fields)
    logger.info(f"Canonical form: {json.dumps(canonical, indent=2)}")


    canonical.pop("post_cards", None)
    canonical.pop("ecp_name", None)
    canonical.pop("ecp_phone_number", None)

    iban = canonical.get("iban", None)

    if not iban or len(iban) < 15:
        logger.error(f"Invalid IBAN: {iban}")
        logger.warning("Excluding IBAN from Conscribo member")
        canonical.pop("iban", None)        

    # Add to Conscribo
    create_relation_member(canonical)


    logger.info("Registration email processed successfully")

