import json
from bs4 import BeautifulSoup
from email import message_from_file
import re
import uuid
from email.message import EmailMessage, Message
from sib_tools.canonical.canonical_key import get_register_form_to_key


def extract_fields_from_mail(path_to_eml):
    msg = message_from_file(open(path_to_eml, 'r', encoding='utf-8'))
    return extract_fields_from_mail_message(msg)

def get_html_and_plain_from_mail_message(msg : EmailMessage):
    html_message = None
    text_message = None
    main_part = next(msg.walk())
    for subpart in main_part.walk():
        if subpart.get_content_type() == 'text/html':
            assert "UTF-8" in subpart['Content-Type'], 'Unexpected Content-Type for text/html'
            assert subpart['Content-Transfer-Encoding'] == 'quoted-printable', 'Unexpected Content-Transfer-Encoding for text/html'
 
            html_message = subpart.get_payload(decode=True)
        if subpart.get_content_type() == 'text/plain':
            assert "UTF-8" in subpart['Content-Type'], 'Unexpected Content-Type for text/plain'
            assert subpart.get('Content-Transfer-Encoding', '') in {'quoted-printable', ''}, 'Unexpected Content-Transfer-Encoding for text/plain'

            text_message = subpart.get_payload(decode=True)

    if html_message is not None:
        print(f"Html message length: {len(html_message)}")
        html_message = html_message.decode('utf-8')
    if text_message is not None:
        print(f"Text message length: {len(text_message)}")
        text_message = text_message.decode('utf-8')

    return html_message, text_message

def extract_fields_from_mail_message(msg : EmailMessage):
    html_message, text_message = get_html_and_plain_from_mail_message(msg)

    # msg.get_body(preferencelist=('related', 'html', 'plain'))
    # iter_attachments()

    if html_message is not None:
        print(f"Html message length: {len(html_message)}")
        secure_bold_marker = str(uuid.uuid4())
        soup = BeautifulSoup(html_message, 'html.parser')
        for tag in soup.find_all('strong'):
            tag.string = f"\n{secure_bold_marker}\n{tag.text}\n"
        parts = soup.text.split(secure_bold_marker)
        preamble = parts[0]
        fields_contents = [
            part.strip().split("\n")
            for part in parts[1:]
        ]
        if len(fields_contents) > 0:
            fields_contents[-1] = fields_contents[-1][:2]
        fields = {
            parts[0].removesuffix(":"): ("\n".join(parts[1:]) if len(parts) > 1 else "")
            for parts in fields_contents
        }
        return fields
    if text_message is not None:
        print(f"Text message length: {len(text_message)}")
        open('member-admin/add-to-conscribo/sample2.txt', 'w', encoding="utf-8").write(text_message)

def form_to_canonical(fields : dict[str, str]) -> dict:
    to_canonical = get_register_form_to_key()
    canonical : dict[str, str] = dict()
    agreements = dict()
    for k, v in fields.items():
        new_key = to_canonical.get(k, None)
        is_agreement = (
            v == "Agree" or v.startswith("Agree\n\nCaptcha response")
        )
        if is_agreement:
            agreements[k] = v
            canonical["agreements_dict"] = agreements            
        if new_key is not None:
            canonical[new_key] = v            
            continue
        if (k in ["id", "form_id", "url_page", "url_slug"]) or is_agreement:
            continue
        other = canonical.setdefault("other", dict())
        other[k] = v
    if "agreements_dict" in canonical:
        del canonical["agreements_dict"]
    canonical["agreements"] = "\n".join([
        f"{k}: {v}"
        for k, v in agreements.items()
    ]) + "\n"
    m = re.fullmatch(
        r"^(\d{1,2})-(\d{1,2})-(\d{4})$",
        canonical["date_of_birth"].strip()
        .replace(" ", "-").replace("/", "-")
    )
    canonical["date_of_birth"] = f"{m.group(3)}-{m.group(2):>02}-{m.group(1):>02}"
    return canonical

# fields = extract_fields_from_mail('member-admin/add-to-conscribo/sample1.eml')
# canonical = form_to_canonical(fields)
# print(json.dumps(canonical, indent=2))

