from attrs import fields
from flask import json
import logging

from sib_tools.email.forms_extract_mail import form_to_canonical

from sib_tools.email.forms_extract_mail import (
    extract_fields_from_mail,
    form_to_canonical,
)

logger = logging.getLogger(__name__)

def process_email(file_path):
    logger.info(f"Processing email file: {file_path}")

    # with open(file_path, 'r') as file:
    #     content = file.read()

    fields = extract_fields_from_mail(file_path)

    canonical = form_to_canonical(fields)
    logger.info(f"Canonical form: {json.dumps(canonical, indent=2)}")


    # Process the content as needed
    # return content