import json
from bs4 import BeautifulSoup
# soup = BeautifulSoup(html_doc, 'html.parser')
from email import message_from_file
import re
import uuid
from canonical_key import get_register_form_to_key

# contents = open('New submission for inschrijfformulier - 2025-02-08 15_14_39.306.eml').read()

def extract_fields_from_mail(path_to_eml):
    msg = message_from_file(open(path_to_eml, 'r', encoding='utf-8'))
    # print(msg)

    print(type(msg))
    print(msg.keys())
    # print(msg.get_content_maintype())

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


    html_message = None
    text_message = None

    # main_part = msg.get_payload()
    main_part = next(msg.walk())
    for subpart in main_part.walk():
        # print(subpart.get_content_type())
        if subpart.get_content_type() == 'text/html':
            print("HTML:")
            assert subpart['Content-Type'] == 'text/html; charset=UTF-8', 'Unexpected Content-Type for text/html'
            assert subpart['Content-Transfer-Encoding'] == 'quoted-printable', 'Unexpected Content-Transfer-Encoding for text/html'

            html_message = subpart.get_payload(decode=True)
        if subpart.get_content_type() == 'text/plain':
            print("TEXT:")
            # print(f"Content-Type: {subpart['Content-Type']}")
            # print(f"Content-Transfer-Encoding: {subpart['Content-Transfer-Encoding']}")
            assert subpart['Content-Type'] == 'text/plain; charset=UTF-8', 'Unexpected Content-Type for text/plain'
            assert subpart['Content-Transfer-Encoding'] == 'quoted-printable', 'Unexpected Content-Transfer-Encoding for text/plain'

            text_message = subpart.get_payload(decode=True)

    # print("--")

    # for part in msg.walk():
    #     # if part.is_multipart():
    #     #     for part.walk():
            

    #     print(part.get_content_type())
    # #     print(part.get_filename())

    # #     if part.get_content_type() == 'text/plain':
    # #         print("\nContent of text/plain:")
    # #         print(part.get_payload())
    # #         print("----\n\n")

    # print(dir(msg))

    # msg.get_body(preferencelist=('related', 'html', 'plain'))
    # iter_attachments()

    # Content-Type: text/plain; charset=UTF-8
    # Content-Transfer-Encoding: quoted-printable

    if html_message is not None:
        print(f"Html message length: {len(html_message)}")
        # open('member-admin/add-to-conscribo/sample1.html', 'wb').write(html_message)
        html_message = html_message.decode('utf-8')

        secure_bold_marker = str(uuid.uuid4())

        soup = BeautifulSoup(html_message, 'html.parser')
        print(soup.text)

        for tag in soup.find_all('strong'):
            tag.string = f"\n{secure_bold_marker}\n{tag.text}\n"

        # for tag in soup.find_all():
        #     print(type(tag))
        #     # print(dir(tag))
        #     print(tag.name)
        #     print(tag.attrs)
        #     # print(tag)

        print(soup.text)
        
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

        # with open("member-admin/add-to-conscribo/sample1-html-extracted.json", "w", encoding="utf-8") as f:
        #     json.dump(fields, f, indent=2)

        return fields


    if text_message is not None:
        print(f"Text message length: {len(text_message)}")
        open('member-admin/add-to-conscribo/sample1.txt', 'wb').write(text_message)
        text_message = text_message.decode('utf-8')

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


fields = extract_fields_from_mail('member-admin/add-to-conscribo/sample1.eml')
canonical = form_to_canonical(fields)
print(json.dumps(canonical, indent=2))

