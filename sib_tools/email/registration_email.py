from email import message_from_bytes, message_from_file
from locale import setlocale
import locale
import logging
import sys
import json
import pytz
from urllib.parse import quote_plus

# After changing something, make sure to run `./restart.sh`. In VS Code:
# - Ctrl+Shift+P
# - Select "Tasks: Run Task"
# - Select "Restart SIB Tools"
#
# After this, the listener for e-mails will be using the new code.

tz = pytz.timezone("Europe/Amsterdam")

from sib_tools.conscribo.groups import add_relations_to_group, find_group_id_by_name
from sib_tools.conscribo.relations import create_relation_member
from sib_tools.email.extract_form_fields import form_to_canonical
from sib_tools.aws.auth import get_ses_client
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

from sib_tools.email.extract_form_fields import (
    extract_fields_from_mail,
    extract_fields_from_mail_message,
    form_to_canonical,
    get_html_and_plain_from_mail_message,
)
from .dkim_verify import DKIMDetailsVerified, DKIMVerifiedMail, verify_dkim_signature
from datetime import datetime, timezone
import re

logger = logging.getLogger("incoming_email.log")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("sib_tools_incoming_email.log")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
# stream_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
logger.addHandler(stream_handler)


def send_registration_notification(
    canonical: dict,
    conscribo_id: str,
    groups_added: list[str],
    original_msg_id: str | None = None,
    original_subject: str | None = None,
    iban_included: bool = True,
):
    """Notify info@sib-utrecht.nl that a registration was processed.
    If original_msg_id is provided, include reply-threading headers.
    """
    try:
        ses = get_ses_client()
        first = canonical.get("first_name", "")
        last = canonical.get("last_name", "")
        email = canonical.get("email", "")

        # Build Conscribo view link
        url_encoded_conscribo_id = quote_plus(str(conscribo_id))
        view_url = (
            f"https://secure.conscribo.nl/sib-utrecht/?module=relationOverview&archive=0&entityType=persoon&filter_code={url_encoded_conscribo_id}&filter_post=1"
        )

        # Because Gmail groups e-mails by subject, we need to reuse the same subject as the original e-mail.
        subject = (
            original_subject
            or f"New registration processed: {first} {last} (Conscribo {conscribo_id})"
        )
        groups_str = ", ".join(groups_added)
        body_html = (
            f"<p>A new registration has been processed by sib-tools.</p>"
            f"<ul>"
            f"<li><strong>Name:</strong> {first} {last}</li>"
            f"<li><strong>Email:</strong> {email}</li>"
            f"<li><strong>Conscribo ID:</strong> {conscribo_id}</li>"
            f"<li><strong>Groups added:</strong> {groups_str}</li>"
            f"</ul>"
            f'<p><a href="{view_url}">View in Conscribo</a></p>'
        )
        body_text = (
            "A new registration has been processed by sib-tools.\n"
            f"Name: {first} {last}\n"
            f"Email: {email}\n"
            f"Conscribo ID: {conscribo_id}\n"
            f"Groups added: {groups_str}\n"
            f"View in Conscribo: {view_url}\n"
        )

        if not iban_included:
            body_text += ("\nNote: The IBAN provided in the registration email was invalid or missing, "
                          "so it was not included in the Conscribo member record.\n")
            body_html += ('<p><strong>Note:</strong> The IBAN provided in the registration email was invalid or missing, '
                          'so it was not included in the Conscribo member record.</p>')


        source = "member-admin-bot@sib-utrecht.nl"
        to_addr = "info@sib-utrecht.nl"

        # Build a MIME email so we can add reply-threading headers
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = source
        msg["To"] = to_addr
        msg["Date"] = formatdate(localtime=False)
        if original_msg_id:
            msg["In-Reply-To"] = original_msg_id
            msg["References"] = original_msg_id
        # Avoid auto-replies and loops
        msg["Auto-Submitted"] = "auto-generated"
        msg["X-Auto-Response-Suppress"] = "All"

        msg.attach(MIMEText(body_text, "plain", _charset="utf-8"))
        msg.attach(MIMEText(body_html, "html", _charset="utf-8"))

        ses.send_raw_email(
            Source=source,
            Destinations=[to_addr],
            RawMessage={"Data": msg.as_string().encode("utf-8")},
        )
        logger.info("Sent registration notification email to info@sib-utrecht.nl")
    except Exception as e:
        logger.error(f"Failed to send registration notification: {e}")


def process_registration_email(dkim_result: DKIMVerifiedMail):
    fields = extract_fields_from_mail_message(dkim_result.email)
    if not fields:
        logger.error("No fields extracted from registration email")
        return

    canonical = form_to_canonical(fields)
    logger.info(f"Canonical form: {json.dumps(canonical, indent=2)}")

    iban = canonical.get("iban", None)
    iban_included = True

    if not iban or len(iban) < 15 or "contact" in iban.lower():
        logger.error(f"Invalid IBAN: {iban}")
        logger.warning("Excluding IBAN from Conscribo member")
        canonical.pop("iban", None)
        iban_included = False

    membership_start = dkim_result.date
    if membership_start is None:
        logger.error("No date found in registration email. Using current date instead.")
        membership_start = datetime.now(timezone.utc).astimezone(tz).isoformat()

    canonical["membership_start"] = membership_start[:10]

    # If the signup is in July or August, set the membership start to September 1st
    if re.fullmatch(r"\d{4}-0[78]-\d+", membership_start[:10]):
        canonical["membership_start"] = f"{membership_start[:4]}-09-01"

    canonical.pop("registration_form_url", None)

    canonical["type"] = "Lid"

    if canonical.get("newsletter_permission"):
        perm = str(canonical["newsletter_permission"]).lower()

        canonical["newsletter_permission"] = (
            perm == "1"
            or ("agree" in perm and not "disagree" in perm)
            or perm == "yes"
            or perm == "ja"
            or perm == "true"
            or "akkoord" in perm
        )

    # Add to Conscribo
    conscribo_id = create_relation_member(canonical, logger)

    groups = [
        "Lid",
        # "eerstejaars",
        # "na 1 februari ingeschreven"
        "Te verwerken",
        "Eerstejaars",
    ]

    for group_name in groups:
        group_id = find_group_id_by_name(group_name)
        if group_id is None:
            logger.error(f"Group '{group_name}' not found")
            continue

        logger.info(
            f"Adding member {repr(canonical['first_name'] + ' ' + canonical['last_name'])} to group {group_name} (ID: {group_id})"
        )
        add_relations_to_group(group_id, [conscribo_id])

    # Notify info@sib-utrecht.nl (include reply-threading headers when possible)
    original_msg_id = dkim_result.email.get("Message-ID") or dkim_result.email.get(
        "Message-Id"
    )
    send_registration_notification(
        canonical,
        conscribo_id,
        groups,
        original_msg_id,
        original_subject=dkim_result.email.get("Subject"),
        iban_included=iban_included,
    )

    logger.info("Registration email processed successfully")


def process_deregistration_email(dkim_result: DKIMDetailsVerified):
    raise NotImplementedError("Deregistration email processing is not implemented yet")

    # for part in dkim_result.email.walk():
    #     if part.get_content_type() != "message/rfc822":
    #         logger.debug(f"Skipping part with content type: {part.get_content_type()}")
    #         continue

    #     subemail = part.get_content()
    #     print(f"Subemail: {subemail}")
    #     print(f"Subemail content type: {part.get_content_type()}")

    #     # if isinstance(subemail, bytes):
    #     #     subemail = subemail.decode('utf-8')
    #     # elif not isinstance(subemail, str):
    #     #     logger.error(f"Unexpected type for subemail: {type(subemail)}")
    #     #     return False

    #     subemail = message_from_bytes(subemail)
    #     from_person = subemail.get("From", "")
    #     print(f"From person: {from_person}")

    #     if part.get_content_type() == 'text/html':
    #         html_content = part.get_payload(decode=True)
    #     elif part.get_content_type() == 'text/plain':
    #         text_content = part.get_payload(decode=True)

    # elm_attachments = dkim_result.email.get_payload(
    #     preferencelist=("application/elm+xml", "application/xml", "text/xml")
    # )
    # if not elm_attachments:
    #     logger.error("No ELM attachments found in deregistration email")
    #     return False

    # if isinstance(elm_attachments, list):
    #     if len(elm_attachments) > 1:
    #         logger.error("Multiple ELM attachments found, expected only one")
    #         return False
    #     elm_attachment = elm_attachments[0]

    # elif isinstance(elm_attachments, str):
    #     elm_attachment = elm_attachments
    # else:
    #     logger.error(f"Unexpected type for ELM attachments: {type(elm_attachments)}")
    #     return False

    # if isinstance(elm_attachment, bytes):
    #     elm_attachment = elm_attachment.decode('utf-8')
    # elif not isinstance(elm_attachment, str):
    #     logger.error(f"Unexpected type for ELM attachment: {type(elm_attachment)}")
    #     return False

    # # Parse the ELM XML
    # try:
    #     elm_data = json.loads(elm_attachment)
    # except json.JSONDecodeError as e:
    #     logger.error(f"Failed to parse ELM XML: {e}")
    #     return False

    # logger.info(f"ELM data: {json.dumps(elm_data, indent=2)}")

    # # html_content, text_content = (
    # #     get_html_and_plain_from_mail_message(dkim_result.email)
    # # )

    # # forwardedHeader = re.compile(
    # #     r"""[.\n]{0,300}\n"""
    # #     r"""---------- Forwarded message ---------\n"""
    # #     r"""Van: [^<\n]*<(?P<sender>[^>\n]+)>\n"""
    # #     r"""Date: (?P<date>[^<\n]+)\n"""
    # # )
    # # # Date can be for example 'za 2 aug 2025 om 16:52'

    # # # text_content = dkim_result.email.get_content("text/plain")
    # # with open("debug.txt", "w") as f:
    # #     f.write("Content of mail:")
    # #     f.write(text_content)

    # # match = forwardedHeader.search(text_content.replace("\r\n", "\n"))

    # # if not match:
    # #     logger.error("No forwarded header found in deregistration email")
    # #     return False

    # # sender = match.group("sender")
    # # date_str = match.group("date").strip()

    # # print(f"Sender: {sender}")
    # # print(f"Date: {date_str}")

    # # # Parse the date
    # # try:
    # #     with setlocale(locale.LC_TIME, "nl_NL.UTF-8"):
    # #         # Assuming the date format is 'za 2 aug 2025 om 16:52'
    # #         date = datetime.strptime(date_str, "%a %d %b %Y om %H:%M")
    # # except ValueError as e:
    # #     logger.error(f"Failed to parse date '{date_str}': {e}")
    # #     return False

    # # logger.info(f"Parsed date: {date.isoformat()}")

    # # fields = extract_fields_from_mail_message(dkim_result.email)

    # # canonical = form_to_canonical(fields)
    # # logger.info(f"Canonical form: {json.dumps(canonical, indent=2)}")

    # # # Extract the member ID from the canonical form
    # # member_id = canonical.get("member_id", None)
    # # if not member_id:
    # #     logger.error("No member ID found in deregistration email")
    # #     return False

    # # # Here you would implement the logic to remove the member from Conscribo
    # # # For now, we just log it
    # # logger.info(f"Deregistering member with ID: {member_id}")
