import email.headerregistry
import email.utils
import json
from bs4 import BeautifulSoup
import re
import uuid
from dataclasses import dataclass
import email
import dkim
from dkim import DKIM, DKIMException
from email.message import EmailMessage
from email.parser import Parser
from email.headerregistry import HeaderRegistry, Address
from email import policy
from logging import Logger

# print(HeaderRegistry().registry)



@dataclass
class DKIMDetailsVerified:
    signing_domain : str
    signing_selector : str | None
    sender : str
    sender_address : Address
    included_headers : list[str]
    date : str | None
    is_forwarded_or_auto: bool | None

@dataclass
class DKIMVerifiedMail(DKIMDetailsVerified):
    email : EmailMessage


def check_aws_ses_verification_headers(msg : EmailMessage):
    auth_results = [
        a.strip()
        for a in msg["Authentication-Results"].split(";")
    ]
    valid_email = re.fullmatch(r".* <(info|secretaris|forms)@sib-utrecht\.nl>", msg["From"])
    if not valid_email:
        raise Exception(f"Invalid sender '{msg['From']}'")
    contains_dkim_pass = next((True for a in auth_results if a.startswith("dkim=pass ")), False)
    contains_spf_pass = next((True for a in auth_results if a.startswith("spf=pass ")), False)
    contains_dmarc_pass = next((True for a in auth_results if a.startswith("dmarc=pass ")), False)
    if not contains_dkim_pass:
        raise Exception("DKIM failed")
    if not contains_spf_pass:
        raise Exception("SPF failed")
    if not contains_dmarc_pass:
        raise Exception("DMARC failed")


def verify_dkim_signature(email_message_eml, logger : Logger, allowed_domains: list[str] | None = None, check_aws_verification_headers = True) -> DKIMVerifiedMail | None:
    """
    Verify DKIM signature of an email message.
    
    Args:
        email_message_eml: Raw email message as bytes or string
        logger: Logger instance for logging
        allowed_domains: Optional list of allowed DKIM domains. If None, any domain is accepted.
        
    Returns:
        DKIMDetailsVerified object if verification succeeds, None otherwise
    """
    try:
        # Convert string to bytes if necessary
        if isinstance(email_message_eml, str):
            email_message_eml = email_message_eml.encode('utf-8')
        
        # Parse the email message
        # message = email.message_from_bytes(email_message_eml)
        # logger.info(f"Email message parsed successfully: {message['Subject']}")
        # logger.info(message)

        logger.info("Starting DKIM verification")

        d = DKIM(email_message_eml, logger=logger)
        try:
            if not d.verify():
                return None
        except DKIMException as x:
            logger.error(f"Error verifying DKIM: {x}")
            return None

        domain = d.domain
        selector = d.selector
        include_headers = d.include_headers
        signed_headers = d.signed_headers

        signed_headers_keys = [k.lower() for k, v in signed_headers]

        # senders = [
        #     v
        #     for (k, v) in signed_headers
        #     if k.lower() == "from" or k.lower() == "sender"
        # ]

        # if not senders:
        #     return None

        # p = Parser(policy=policy.default)
        # message = p.parse(email_message_eml, headersonly=True)
        message = email.message_from_bytes(email_message_eml, policy=policy.default)


        email_from : tuple[Address, ...] = message["from"].addresses
        if not email_from:
            logger.error("Missing from")
            return None
        
        email_sender = message.get("sender")
        if email_sender:
            email_sender : Address | None = email_sender

        # SECURITY: Define ALL headers that MUST be signed for security
        required_signed = [
            b"from", b"to", b"subject", b"date"
        ]

        # SECURITY: If sender header exists, it MUST be signed
        if email_sender:
            required_signed.append(b"sender")

        if "message-id" in message:
            required_signed.append(b"message-id")
            logger.debug("Message-ID header found, requiring it to be signed")
            
        # SECURITY: Check for other security-critical headers that should be signed if present
        security_critical_headers = [b"reply-to", b"message-id"]
        for header in security_critical_headers:
            if header.decode('ascii') in message:
                required_signed.append(header)
                logger.debug(f"Found security-critical header '{header.decode('ascii')}', requiring it to be signed")

        logger.info(f"Signed header keys: {signed_headers_keys}")
        logger.info(f"Required signed headers: {[h.decode('ascii') for h in required_signed]}")

        for header in required_signed:
            if header in signed_headers_keys:
                continue

            logger.error(f"Header {header} not signed")
            return None

        if email_sender is None and len(email_from) == 1:
            email_sender = email_from[0]

        if email_sender is None:
            logger.error("Email sender is None")
            return None
        
        # Check if sender is included in 'from':
        from_addresses = [addr.addr_spec for addr in email_from]
        if email_sender.addr_spec not in from_addresses:
            logger.error(f"Email sender {email_sender.addr_spec} not in 'from' addresses: {from_addresses}")
            return None
        
        email_sender_domain = email_sender.domain.encode("utf-8")

        # SECURITY: Strict domain matching - must be exact match, no subdomains
        if email_sender_domain != domain:
            logger.error(f"Email sender domain {email_sender_domain} does not match DKIM domain {domain}")
            return None
            
        # SECURITY: Optional domain validation if allowed_domains is specified
        if allowed_domains is not None:
            domain_str = domain.decode('ascii')
            if domain_str not in allowed_domains:
                logger.error(f"DKIM domain {domain_str} is not in allowed domains: {allowed_domains}")
                return None

        logger.info(f"From: {email_from}")
        logger.info(f"Sender: {email_sender}")
        logger.info(f"DKIM verified for domain: {domain}, selector: {selector}")

        # Extract the date header
        date_header : str | None = message.get("date")
        date_str : str | None = None
        if date_header:
            date_datetime = email.utils.parsedate_to_datetime(date_header)
            date_str = date_datetime.isoformat()

        if "x-autoreply" in message:
            logger.error("Email has X-Autoreply header")
            return None

        if "auto-submitted" in message:
            logger.error("Email has Auto-Submitted header")
            return None

        is_forwarded_or_auto = False
        # Check for forwarding/auto-generated headers
        for header in ["Resent-From", "Auto-Submitted", "Return-Path", "X-Autoreply"]:
            if header in message:
                logger.info(f"Detected forwarding/auto-generated header: {header}")
                is_forwarded_or_auto = True

        if check_aws_verification_headers:
            # SECURITY: Check AWS SES verification headers
            try:
                check_aws_ses_verification_headers(message)
                logger.info("AWS SES verification headers are valid")
            except Exception as e:
                logger.error(f"Failed AWS SES verification: {e}")
                return None

        return DKIMVerifiedMail(
            signing_domain=domain.decode('ascii'),
            signing_selector=selector.decode('ascii') if selector else None,
            sender=email_sender.addr_spec,
            sender_address=email_sender,
            included_headers=[a.decode("ascii") for a in include_headers],
            date=date_str if date_header else None,
            email=message,
            is_forwarded_or_auto=is_forwarded_or_auto
        )
        
    except Exception:
        logger.error("Error during DKIM verification", exc_info=True)
        # Return None if any error occurs during verification
        return None

