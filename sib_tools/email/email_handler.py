import sys
import logging
import json
from datetime import datetime, timezone, timedelta

from .forms_extract_mail import extract_fields_from_mail, extract_fields_from_mail_message, form_to_canonical
from .dkim_verify import DKIMDetailsVerified, verify_dkim_signature
from dataclasses import asdict

def handle_incoming_email(args) -> bool:
    eml_path = args.eml_path
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)

    try:
        with open(eml_path, "rb") as eml_file:
            allowed_domains = ["sib-utrecht.nl"]
            dkim_result = verify_dkim_signature(eml_file.read(), logger=logger, allowed_domains=allowed_domains)

        if not dkim_result:
            logger.error("DKIM verification failed")
            return False
        
        logger.debug(f"DKIM domain: {dkim_result.signing_domain}")

        # SECURITY: Strict domain validation
        if dkim_result.signing_domain != "sib-utrecht.nl":
            logger.error(f"Unexpected DKIM domain: {json.dumps(dkim_result.signing_domain)}")
            return False
        
        logger.debug(f"DKIM selector: {dkim_result.signing_selector}")
        logger.debug(f"Email sender: {dkim_result.sender}")

        # SECURITY: Whitelist of allowed sender addresses - must be exact match
        allowed_senders = [
            "info@sib-utrecht.nl",
            "secretaris@sib-utrecht.nl",
        ]
        
        if dkim_result.sender not in allowed_senders:
            logger.error(f"Unexpected email sender: {json.dumps(dkim_result.sender)}")
            return False
        
        if dkim_result.date is None:
            logger.error("Email has no date header")
            return False
                
        # SECURITY: Time-based validation to prevent replay attacks
        if not args.allow_old:
            try:
                email_date = datetime.fromisoformat(dkim_result.date.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                
                # Allow emails from up to 24 hours ago, but not future emails
                if email_date > now + timedelta(minutes=5):  # 5 min tolerance for clock skew
                    logger.error(f"Email date is in the future: {email_date}")
                    return False
                    
                if email_date < now - timedelta(hours=24):
                    logger.error(f"Email is too old (older than 24 hours): {email_date}")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to parse email date: {e}")
                return False

        message = dkim_result.email
        dkim_result.email = None

        logger.info(f"DKIM verified: {dkim_result}")
        details = asdict(dkim_result)
        details.pop("email", None)  # Remove email from details
        details["included_headers"] = ", ".join(dkim_result.included_headers)

        logger.debug(f"DKIM details: {json.dumps(details, indent=2, default=str)}")

        fields = extract_fields_from_mail_message(message)
        canonical = form_to_canonical(fields)
        logger.info(f"Canonical form: {json.dumps(canonical, indent=2)}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to process email: {e}")
        sys.exit(1)


def add_parse_args(parser):
    parser.add_argument("eml_path", help="Path to the .eml file to process")
    parser.add_argument(
        "--allow-old",
        action="store_true",
        help="Allow processing of emails older than 24 hours (for testing purposes only)",
    )
    parser.set_defaults(func=handle_incoming_email)
