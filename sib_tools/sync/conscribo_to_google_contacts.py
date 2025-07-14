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
from datetime import datetime, date, timezone


CONTACTS_SCOPES = [
    "https://www.googleapis.com/auth/contacts",
    "https://www.googleapis.com/auth/contacts.readonly",
]


def sync_conscribo_to_google_contacts(dry_run=False):
    """
    Sync Conscribo members to Google Contacts, only considering contacts with label 'Member'.
    Uses the Google People API.
    """

    try:
        print("Syncing Conscribo members to Google Contacts...")

        creds = get_credentials(CONTACTS_SCOPES)
        service = build("people", "v1", credentials=creds)

        group = get_contact_group(service, GOOGLE_CONTACTS_MEMBER_LABEL)
        if not group:
            print("No contact group with label 'Member' found, creating it...")
            # group = service.contactGroups().create(
            #     body={"name": "Member", "groupType": "USER_CONTACT_GROUP"}
            # ).execute()
            # print(f"Created group: {group.get('resourceName')}")
            return

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

        print(
            f"Would add {len(would_add)} contacts, would remove {len(would_remove)} contacts."
        )

        today = datetime.now(tz=timezone.utc).astimezone()
        print(f"Sync date: {today.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Dry run: {dry_run}")

        today_date = today.date().isoformat()

        this_year = today.year

        print("Add: ")
        for conscribo_id in would_add:
            member = members_by_conscribo_id[conscribo_id]
            print(
                f" - {member['first_name']} {member['last_name']} <{member['email']}> ({conscribo_id})"
            )

            if dry_run:
                continue

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

            this_year_birthday = f"{this_year}-{date_of_birth[5:7]}-{date_of_birth[8:10]}"
            next_year_birthday = f"{this_year + 1}-{date_of_birth[5:7]}-{date_of_birth[8:10]}"

            next_birthday = None
            age_at_next_birthday = this_year - int(date_of_birth[:4]) if date_of_birth else 0

            if this_year_birthday >= today_date:
                next_birthday = this_year_birthday
            else:
                next_birthday = next_year_birthday
                age_at_next_birthday += 1

            contact = {
                "names": [
                    {
                        "givenName": member["first_name"],
                        "familyName": member["last_name"],
                    }
                ],
                "emailAddresses": [
                    {"value": member["email"], "metadata": {"primary": True}}
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
                            f"{member['first_name']} {member['last_name']} - Anoniem Nr: XXX\n"
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

            # Create contact in Google Contacts
            created_contact = service.people().createContact(body=contact).execute()
            sleep(0.3)
            
            # Add to the contact group
            service.contactGroups().members().modify(
                resourceName=group["resourceName"],
                body={"resourceNamesToAdd": [created_contact["resourceName"]]}
            ).execute()

            print(f"Created contact: {created_contact.get('resourceName')}")
            print(json.dumps(created_contact, indent=2))
            sleep(0.1)  # Avoid hitting rate limits
            break

        print("Remove: ")
        for conscribo_id in would_remove:
            contact = contacts_by_conscribo_id[conscribo_id]
            print(
                f" - {contact['first_name']} {contact['last_name']} <{contact['email']}> ({conscribo_id})"
            )

            if dry_run:
                continue

            resource_name = contact.get("other", {}).get("googleResourceName")
            if not resource_name:
                logging.warning(
                    f"Contact {contact['conscribo_id']} does not have a Google resource name, skipping removal."
                )
                continue

            # Remove contact from Google Contacts
            service.people().deleteContact(resourceName=resource_name).execute()
            sleep(0.1)

    except Exception as e:
        logging.exception(f"Error syncing to Google Contacts: {e}")
