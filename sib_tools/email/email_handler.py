import sys
import logging
import json
from datetime import datetime, timezone, timedelta

from .extract_form_fields import extract_fields_from_mail, extract_fields_from_mail_message, form_to_canonical
from .dkim_verify import DKIMDetailsVerified, verify_dkim_signature
from dataclasses import asdict
from .registration_email import logger, process_registration_email, process_deregistration_email

def handle_incoming_email(args):
    eml_path = args.eml_path
    allow_old = args.allow_old

    if not eml_path:
        print("No .eml file provided")
        sys.exit(1)

    if not process_email(eml_path, allow_old):
        print("Email processing failed")
        sys.exit(1)

    print("Email processed successfully")
    return 0


def process_email(eml_path, allow_old=False) -> bool:
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
        logger.debug(f"Email date: {dkim_result.date}")
        logger.debug(f"Subject: {json.dumps(dkim_result.email['Subject'])}")

        # SECURITY: Whitelist of allowed sender addresses - must be exact match
        allowed_senders = [
            "info@sib-utrecht.nl",
            "secretaris@sib-utrecht.nl",
            "forms@sib-utrecht.nl"
        ]
        
        if dkim_result.sender not in allowed_senders:
            logger.error(f"Unexpected email sender: {json.dumps(dkim_result.sender)}")
            return False
        
        if dkim_result.date is None:
            logger.error("Email has no date header")
            return False
                
        # SECURITY: Time-based validation to prevent replay attacks
        if not allow_old:
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
        # dkim_result.email = None

        # logger.info(f"DKIM verified: {dkim_result}")
        details = asdict(dkim_result)
        details.pop("email", None)  # Remove email from details
        details["included_headers"] = ", ".join(dkim_result.included_headers)

        logger.debug(f"DKIM details: {json.dumps(details, indent=2, default=str)}")

        receiver = extract_receiver_address(message)

        logger.info(f"Receiver: {receiver}")

        if dkim_result.sender == "forms@sib-utrecht.nl":
            reply_to = message.get("Reply-To", None)
            if reply_to:
                reply_to = reply_to.addresses

            if not reply_to:
                logger.error("No Reply-To header found in the email. Can't verify it is not a user-facing e-mail.")
                return False

            reply_to = reply_to[0]

            if ("sib-utrecht.nl" in reply_to.domain) or ("sibutrecht.nl" in reply_to.domain):
                logger.error(f"Reply-To address {reply_to} is not of a user, the mail may hence be a user-facing e-mail. Aborting processing.")
                return False
        
        # Check an '@automations.sib-utrecht.nl' is included in 'To'
        included_to_addresses = [
            address.addr_spec
            for address in message.get("to").addresses
            if address.domain == "automations.sib-utrecht.nl"
        ]
        
        if not included_to_addresses and dkim_result.sender != "forms@sib-utrecht.nl":
            logger.error("No '@automations.sib-utrecht.nl' address found in 'To' header")
            return False

        # In the case of a forwarded e-mail, this can differ from the receiver
        delivered_to_address = message.get("Delivered-To", None)
        if delivered_to_address:
            logger.info(f"Delivered to: {delivered_to_address}")
            if not delivered_to_address.endswith("@sib-utrecht.nl"):
                logger.error(f"Delivered-To address {delivered_to_address} is not a sib-utrecht.nl address")
                return False


        if receiver not in included_to_addresses and dkim_result.sender != "forms@sib-utrecht.nl":
            logger.error(f"Receiver {receiver} not found in 'To' header")
            return False
        
        if receiver in ["inschrijving@automations.sib-utrecht.nl", "register@automations.sib-utrecht.nl"]:
            logger.info(f"Processing registration email for: {receiver}")
            process_registration_email(dkim_result)
            return True

        if receiver in ["deregister@automations.sib-utrecht.nl"]:
            logger.info(f"Processing deregistration email for: {receiver}")
            process_deregistration_email(dkim_result)
            return True

        logger.error(f"Unexpected receiver address: {receiver}. No handler")

    except Exception as e:
        logger.error(f"Failed to process email: {e}", exc_info=True)
        sys.exit(1)


def extract_receiver_address(message):
    """
    Extract the e-mail address to which the e-mail was delivered.
    Returns the first address found in the 'Delivered-To' header, or, if absent, attempts to extract from the 'Received' headers,
    and finally falls back to the 'To' header.
    """
    # Fallback: try to extract from Received headers
    received_headers = message.get_all('received', [])
    import re
    for header in received_headers:
        # Look for 'for <email@domain>' in the header
        match = re.search(r'for <([^>]+)>', header)
        if match:
            return match.group(1)
    
    delivered_to = message.get_all('delivered_to', [])
    if delivered_to:
        # If multiple Delivered-To headers, return the first one
        return delivered_to[0]
    # Final fallback: use the 'To' header
    to_header = message.get_all('to', [])
    if to_header:
        # The 'To' header may contain multiple addresses, separated by commas
        from email.utils import getaddresses
        addresses = getaddresses(to_header)
        if addresses:
            # Return the first email address found
            return addresses[0][1]
    return None


def add_parse_args(parser):
    parser.add_argument("eml_path", help="Path to the .eml file to process")
    parser.add_argument(
        "--allow-old",
        action="store_true",
        help="Allow processing of emails older than 24 hours (for testing purposes only)",
    )
    parser.set_defaults(func=handle_incoming_email)
