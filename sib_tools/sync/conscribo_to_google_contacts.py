"""
Sync Conscribo members to Google Contacts, only considering contacts with label 'Member'.
"""

from sib_tools.google.auth import get_credentials
from googleapiclient.discovery import build
import logging
import json
from time import sleep
from ..google.contacts import (
    list_google_contacts,
    get_contact_group,
    GOOGLE_CONTACTS_MEMBER_LABEL,
)
from ..conscribo.relations import (
    list_relations_active_members,
)
from datetime import datetime, date, timezone, timedelta
from ..utils import print_change_count, print_header
from random import randint
from pathlib import Path

CONTACTS_SCOPES = [
    "https://www.googleapis.com/auth/contacts",
    "https://www.googleapis.com/auth/contacts.readonly",
]

"""
Wat zijn anonieme nummers?
==========================

Stel er is een lid van SIB, 'Jan Kasteele' (bedachte naam).
In de notulen van een BV (bestuursvergadering) is het handig om deze persoon
te vermelden. Bijvoorbeeld:

> Door dat incident voelde Jan Kasteele zich ongemakkelijk, laten we hierop letten.

Het is handig voor het bestuur om terug te kunnen vinden over wie het gaat, maar
je wil niet dat volgende besturen, die weinig afweten van de situatie, hier thee
van gaan maken. En ook niet dat de persoon gevoel kan hebben dat er over hem
gesproken blijft worden, dat een gebeurtenis hem blijft achtervolgen.

Om die redenen werden notulen in het verleden vaak verwijderd door elk uitgaande
bestuur. Bij het 44e bestuur is er een nieuwe oplossing bedacht, waardoor dit
geen probleem meer is:

Je voegt een contact toe aan Google Contacts:

Naam: Jan Kasteele
E-mail: member104@anon.sib-utrecht.nl

Vervolgens kan je in o.a. Google Docs gebruik maken van een smart chip; je
typt '@' en begint de naam van de persoon te typen. Je krijgt suggesties van
personen. Kies de 'Jan Kasteele', met dit memberXXX@anon.sib-utrecht.nl 
e-mailadres. 

> Door dat incident voelde @Jan... zich ongemakkelijk, laten we hierop letten.

Dit komt in het document te zien als een smartchip op die plek, dus

> Door dat incident voelde [member104@anon.sib-utrecht.nl] zich ongemakkelijk, laten we hierop letten.

Het belangrijke is dat het document enkel het e-mailadres bevat. Maar als je met
je muis erover hovert, toont het je het contact met dat e-mailadres. In het
geval van een Gmail / Google e-mailadres zou het de contactnaam wel direct tonen
en opslaan in het document, maar dus niet bij een ander e-mailadres gelukkig.

Dit betekent dat je tijdens je bestuursjaar met een kleine moeite kan bekijken
over welke persoon het gaat, en dat je aan het einde van je bestuursjaar alle
contacten kan verwijderen, en daarmee dat een volgend bestuur niet kan weten
over wie het gaat.

Deze contacten worden toegevoegd door sib-tools, zie
https://github.com/sib-utrecht/sib-utrecht-tools. We raden aan dat volgende
besturen dit systeem blijven gebruiken, of een equivalente oplossing gebruiken.

Opmerking: door het 44e bestuur zijn contacten 1-180 gebruikt. We raden aan dat
elk bestuur een nieuw blok van 200 of 300 nummers gebruikt, zodat je niet hebt
dat oude notulen schijnbaar refereren aan nieuwe leden. Dit mechanisme zit ook
verwerkt in sib-tools.

Groetjes,
Vincent Kuhlmann

"""


ANON_MIN_AVAILABILITY = 20
ANON_BLOCK_SIZE = 300

ANON_NUMBER_FILE = Path(__file__).parent.parent.parent / "anon_number.json"

def get_fresh_anon_number():
    if not ANON_NUMBER_FILE.exists():
        print("Warning: anon_number.json does not exist, creating new file.")

        with ANON_NUMBER_FILE.open("w") as f:
            json.dump({
                "next_start": 200,
                "available": [],
                "available_expiry": None
            }, f, indent=2)

    with ANON_NUMBER_FILE.open("r") as f:
        data = json.load(f)

    today = datetime.now(tz=timezone.utc).astimezone()
    today_date = today.date().isoformat()
    
    available_expiry = data.get("available_expiry")
    expired = today_date > available_expiry if available_expiry else True
    
    available = []
    if not expired:
        available = data.get("available", [])

    if len(available) < ANON_MIN_AVAILABILITY:
        start = data.get("next_start", 200)
        new_available = list(range(start, start + ANON_BLOCK_SIZE))
        available.extend(new_available)
        data["next_start"] = start + ANON_BLOCK_SIZE
        data["available_expiry"] = (date.today() + timedelta(days=30*10)).isoformat()

    choice = randint(0, len(available) - 1)
    number = available.pop(choice)
    data["available"] = available

    with ANON_NUMBER_FILE.open("w") as f:
        json.dump(data, f)

    return number


def do_add(contact, logger: logging.Logger, dry_run: bool, service, group):
    today = datetime.now(tz=timezone.utc).astimezone()
    today_date = today.date().isoformat()
    this_year = today.year

    member = contact
    logger.info(
        f" - {member['first_name']} {member['last_name']} <{member['email']}> ({member.get('conscribo_id')})"
    )

    if dry_run:
        return

    birthdays = []
    date_of_birth = member.get("date_of_birth")
    if date_of_birth:
        birthdays.append(
            {
                "date": {
                    "year": date_of_birth[:4],
                    "month": date_of_birth[5:7],
                    "day": date_of_birth[8:10],
                },
                "text": date_of_birth,
                "metadata": {"primary": True},
            }
        )

    next_birthday = None
    age_at_next_birthday = 0

    if date_of_birth:
        age_at_next_birthday = this_year - int(date_of_birth[:4]) if date_of_birth else 0

        this_year_birthday = f"{this_year}-{date_of_birth[5:7]}-{date_of_birth[8:10]}"
        next_year_birthday = f"{this_year + 1}-{date_of_birth[5:7]}-{date_of_birth[8:10]}"

        if this_year_birthday >= today_date:
            next_birthday = this_year_birthday
        else:
            next_birthday = next_year_birthday
            age_at_next_birthday += 1

    anon_number = get_fresh_anon_number()
    anon_email = f"member{anon_number}@anon.sib-utrecht.nl"
    phone_number = member.get("phone_number", None)

    contact = {
        "names": [
            {
                "givenName": member["first_name"],
                "familyName": member["last_name"],
            }
        ],
        "emailAddresses": [
            {"value": member["email"], "metadata": {"primary": True}},
            {"value": anon_email, "type": "dummy", "formattedType": "Dummy", "metadata": {"primary": False}},
        ],
        "userDefined": [
            {
                "key": "Conscribo Relatienummer",
                "value": str(member["conscribo_id"]),
            }
        ],
        "biographies": [
            {
                "value": (
                    f"{member['first_name']} {member['last_name']}\n"
                    f"Leeftijd: wordt {age_at_next_birthday} jaar op {next_birthday}\n"
                    f"\n"
                    f"Begin lidmaatschap: {member.get('membership_start')}"
                ),
                "contentType": "TEXT_PLAIN",
                "metadata": {"primary": True},
            }
        ],
    }

    if birthdays:
        contact["birthdays"] = birthdays

    if phone_number:
        contact["phoneNumbers"] = [
            {"value": phone_number, "type": "mobile", "formattedType": "Mobile"}
        ]

    # Create contact in Google Contacts
    created_contact = service.people().createContact(body=contact).execute()
    sleep(0.3)
    
    # Add to the contact group
    service.contactGroups().members().modify(
        resourceName=group["resourceName"],
        body={"resourceNamesToAdd": [created_contact["resourceName"]]}
    ).execute()

    logger.info(f"    Created contact: {created_contact.get('resourceName')}")
    # logger.debug(json.dumps(created_contact, indent=2))
    sleep(0.1)  # Avoid hitting rate limits
    # break


def sync_conscribo_to_google_contacts(dry_run=False, logger: logging.Logger | None = None) -> int:
    """
    Sync Conscribo members to Google Contacts, only considering contacts with label 'Member'.
    Uses the Google People API.
    """

    logger = logger or logging.getLogger(__name__)

    try:
        print_header("Syncing Conscribo members to Google Contacts...", logger)

        creds = get_credentials(CONTACTS_SCOPES)
        service = build("people", "v1", credentials=creds)

        group = get_contact_group(service, GOOGLE_CONTACTS_MEMBER_LABEL)
        if not group:
            logger.warning("No contact group with label 'Member' found, create one to continue.")
            # group = service.contactGroups().create(
            #     body={"name": "Member", "groupType": "USER_CONTACT_GROUP"}
            # ).execute()
            # logger.info(f"Created group: {group.get('resourceName')}")
            return 0

        members = list_relations_active_members()
        members_by_conscribo_id = {member["conscribo_id"]: member for member in members}

        contacts = list_google_contacts(label_name=GOOGLE_CONTACTS_MEMBER_LABEL)
        contacts_by_conscribo_id = {
            contact.get("conscribo_id"): contact for contact in contacts
        }

        would_add = set(members_by_conscribo_id.keys()) - set(
            contacts_by_conscribo_id.keys()
        )
        would_remove = set(contacts_by_conscribo_id.keys()) - set(
            members_by_conscribo_id.keys()
        )

        logger.info(
            f"Would add {len(would_add)} contacts, would remove {len(would_remove)} contacts."
        )

        today = datetime.now(tz=timezone.utc).astimezone()
        logger.info(f"Sync date: {today.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"Dry run: {dry_run}")

        change_count = len(would_add) + len(would_remove)

        logger.info("Add: ")
        for conscribo_id in would_add:
            member = members_by_conscribo_id[conscribo_id]
            do_add(member, logger, dry_run, service=service, group=group)

        logger.info("Remove: ")
        for conscribo_id in would_remove:
            contact = contacts_by_conscribo_id[conscribo_id]
            logger.info(
                f" - {contact['first_name']} {contact['last_name']} <{contact['email']}> ({conscribo_id})"
            )
            logger.info(f"  Was: {json.dumps(contact, indent=4)}")

            if dry_run:
                continue

            resource_name = contact.get("other", {}).get("googleResourceName")
            if not resource_name:
                logger.warning(
                    f"Contact {contact['conscribo_id']} does not have a Google resource name, skipping removal."
                )
                continue

            # Remove contact from Google Contacts
            service.people().deleteContact(resourceName=resource_name).execute()
            sleep(0.1)

        print_change_count(change_count, logger)
        return change_count

    except Exception as e:
        logger.exception(f"Error syncing to Google Contacts: {e}")
        return 0
