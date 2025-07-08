"""
Synchronize Conscribo members to Google Groups (mailing lists).
"""

from sib_tools.conscribo.relations import (
    list_relations_active_alumni,
    list_relations_active_members,
)
from sib_tools.google.auth import (
    list_group_members_api,
    get_credentials,
    directory_scopes,
)
from googleapiclient.discovery import build
from time import sleep

# Example: mapping Conscribo roles to Google Groups
GROUPS = {
    "members@sib-utrecht.nl": "member",
    "": "alumnus",
}


def sync_group_to_emails(group_email, emails, dry_run=True):
    creds = get_credentials(directory_scopes)
    service = build("admin", "directory_v1", credentials=creds)

    print(f"Syncing group: {group_email}. Got {len(emails)} emails")
    print(f"Dry run: {dry_run}")

    # Get current Google Group members
    google_members = list_group_members_api(group_email)
    google_emails = set(m.get("email") for m in google_members if m.get("email"))
    google_always_stay = set(
        m.get("email")
        for m in google_members
        if (
            m.get("role") in ["MANAGER", "OWNER"]
            or m.get("email", "").endswith("@sib-utrecht.nl")
        )
    )

    will_add = emails - google_emails
    will_remove = (google_emails - emails) - google_always_stay

    print(f"Emails in Google list: {len(google_emails)}")
    print(
        f"Will remove {len(will_remove)} emails, will add {len(will_add)}"
    )
    print()
    print()

    # Remove extra members from Google Group
    for email in will_remove:
        print(f"Removing {email} from {group_email}")
        if dry_run:
            continue

        try:
            service.members().delete(groupKey=group_email, memberKey=email).execute()
        except Exception as e:
            print(f"Failed to remove {email}: {e}")
        sleep(0.2)

    print()
    # Add missing members to Google Group
    for email in will_add:
        print(f"Adding {email} to {group_email}")
        if dry_run:
            continue

        try:
            service.members().insert(
                groupKey=group_email, body={"email": email, "role": "MEMBER"}
            ).execute()
        except Exception as e:
            print(f"Failed to add {email}: {e}")
        sleep(0.2)


def sync_conscribo_to_google_groups(dry_run=True, group="alumni"):
    """
    Synchronize Conscribo members to Google Groups.
    group: 'alumni' or 'members'
    """
    if group == "alumni":
        print("Syncing alumni emails:")
        alumni = list_relations_active_alumni()
        emails = set(a.get("email") for a in alumni) - {"", None}
        sync_group_to_emails("alumni@sib-utrecht.nl", emails, dry_run=dry_run)
    elif group == "members":
        print("Syncing members emails:")
        members = list_relations_active_members()
        emails = set(a.get("email") for a in members) - {"", None}
        sync_group_to_emails("members@sib-utrecht.nl", emails, dry_run=dry_run)
    else:
        raise ValueError(f"Unknown group: {group}")
