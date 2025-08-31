"""
Sync Conscribo members to Google Contacts, only considering contacts with label 'Member'.
"""

from sib_tools.google.auth import get_credentials
from googleapiclient.discovery import build
import logging
import json

CONTACTS_SCOPES = [
    "https://www.googleapis.com/auth/contacts",
    "https://www.googleapis.com/auth/contacts.readonly",
]

GOOGLE_CONTACTS_MEMBER_LABEL = "Member"


def contact_to_canonical(contact):
    primary_email = next((
        email for email in contact.get("emailAddresses", [])
        if email.get("metadata", {}).get("primary")
    ), {}).get("value")

    dummy_email = next((
        email for email in contact.get("emailAddresses", [])
        if email.get("type") == "Dummy"
    ), {}).get("value")

    user_defined_map = {
        ud.get("key"): ud.get("value")
        for ud in contact.get("userDefined", [])
    }

    primary_name = next((
        name for name in contact.get("names", [])
        if name.get("metadata", {}).get("primary")
    ), {})

    primary_birthday = next((
        b for b in contact.get("birthdays", [])
        if b.get("metadata", {}).get("primary")
    ), {})

    date = primary_birthday.get("date", {})
    date_of_birth_2 = f"{date.get('year', 'YYYY')}-{date.get('month', 'MM'):02}-{date.get('day', 'DD'):02}"

    metadata = contact.get("metadata", {})
    sources = metadata.get("sources", [])

    updateTime = None
    contactType = None
    contactId = None

    if sources:
        source = sources[0]
        updateTime = source.get("updateTime")
        contactType = source.get("type")
        contactId = source.get("id")

    return {
        "conscribo_id": user_defined_map.get("Conscribo Relatienummer", None),
        "first_name": primary_name.get("givenName", None),
        "last_name": primary_name.get("familyName", None),
        "email": primary_email,
        "phone_number": (contact.get("phoneNumbers") or [{}])[0].get("value"),
        "date_of_birth": primary_birthday.get("text"),
        "anon_number": user_defined_map.get("AnoniemNr", None),
        "anon_email": dummy_email,
        "other": {
            "date_of_birth_2": date_of_birth_2,
            "display_name": primary_name.get("displayName", ""),
            "googleResourceName": contact.get("resourceName", ""),
            "googleEtag": contact.get("etag", ""),
            "objectType": contact.get("metadata", {}).get("objectType", ""),
            "updateTime": updateTime,
            "contactType": contactType,
            "googleContactId": contactId,
        }
    }

def get_contact_group(service, group_name):
    """
    Get a contact group by name.
    """
    groups_result = service.contactGroups().list(pageSize=200).execute()
    groups = groups_result.get("contactGroups", [])
    for group in groups:
        if group.get("name") == group_name:
            return group
    return None

def list_google_contacts(label_name=GOOGLE_CONTACTS_MEMBER_LABEL, raw=False, limit=None, offset=0):
    creds = get_credentials(CONTACTS_SCOPES)
    service = build("people", "v1", credentials=creds)

    print(f"Fetching contacts with label '{label_name}' from Google People API...")
    # Get all contact groups (labels)
    member_group = get_contact_group(service, label_name)
    if not member_group:
        raise Exception(f"No Google Contact group with label '{label_name}' found.")

    member_group_id = member_group["resourceName"]
    # List all contacts (connections) using the People API
    contacts = []
    page_token = None
    while True:
        connections_result = service.people().connections().list(
            resourceName="people/me",
            personFields="names,emailAddresses,memberships,birthdays,biographies,metadata,relations,userDefined",
            pageSize=1000,
            pageToken=page_token
        ).execute()
        connections = connections_result.get("connections", [])
        contacts.extend(connections)
        page_token = connections_result.get("nextPageToken")
        if not page_token:
            break
    print(f"Found {len(contacts)} contacts in total.")
    member_contacts = []
    for person in contacts:
        memberships = person.get("memberships", [])
        if any(
            m.get("contactGroupMembership", {}).get("contactGroupResourceName") == member_group_id
            for m in memberships
        ):
            member_contacts.append(person)
    print(f"Found {len(member_contacts)} contacts with label '{label_name}'.")

    # Apply offset and limit
    member_contacts = member_contacts[offset:offset+limit] if limit is not None else member_contacts[offset:]

    if raw:
        return member_contacts
    else:
        return [contact_to_canonical(contact) for contact in member_contacts if contact.get("names")]

    # for contact in member_contacts:
    #     names = contact.get("names", [])
    #     displayname = names[0]["displayName"] if names else "(No Name)"

    #     canonical_contact = contact_to_canonical(contact)
    #     # print(f"Contact {displayname}: {json.dumps(canonical_contact, indent=2)}")

