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
import logging
from datetime import datetime, timezone
from ..utils import print_change_count, print_header


def sync_group_to_emails(group_email, emails, dry_run=True, logger: logging.Logger | None = None) -> int:
    logger = logger or logging.getLogger(__name__)

    creds = get_credentials(directory_scopes)
    service = build("admin", "directory_v1", credentials=creds)

    logger.info(f"Syncing group: {group_email}. Got {len(emails)} emails")
    logger.info(f"Dry run: {dry_run}")

    # Get current Google Group members
    google_members = list_group_members_api(group_email)
    google_emails = set(m.get("email") for m in google_members if m.get("email"))

    # Google may change the case of e-mail addresses, so let's change case when
    # necessary.
    google_emails_case = {email.lower(): email for email in google_emails}
    for email in list(emails):
        if email in google_emails:
            continue

        preferred_case = google_emails_case.get(email.lower())
        if not preferred_case:
            continue

        emails.remove(email)
        emails.add(preferred_case)

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

    logger.info(f"Emails in Google list: {len(google_emails)}")
    logger.info(
        f"Will remove {len(will_remove)} emails, will add {len(will_add)}"
    )
    logger.info("")
    logger.info("")

    change_count = len(will_add) + len(will_remove)

    # Remove extra members from Google Group
    for email in will_remove:
        logger.info(f"Removing {email} from {group_email}")
        if dry_run:
            continue

        try:
            service.members().delete(groupKey=group_email, memberKey=email).execute()
        except Exception as e:
            logger.warning(f"Failed to remove {email}: {e}")
        sleep(0.2)

    logger.info("")
    # Add missing members to Google Group
    for email in will_add:
        logger.info(f"Adding {email} to {group_email}")
        if dry_run:
            continue

        try:
            service.members().insert(
                groupKey=group_email, body={"email": email, "role": "MEMBER"}
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to add {email}: {e}")
        sleep(0.2)

    print_change_count(change_count, logger)
    return change_count


def sync_conscribo_to_google_groups(dry_run=True, group="alumni", logger: logging.Logger | None = None) -> int:
    """
    Synchronize Conscribo members to Google Groups.
    group: 'alumni' or 'members'
    """
    logger = logger or logging.getLogger(__name__)

    print_header(f"Syncing Conscribo emails to Google Group ({group})...", logger)

    if group == "alumni":
        logger.info("Syncing alumni emails:")
        alumni = list_relations_active_alumni()
        emails = set(a.get("email") for a in alumni) - {"", None}
        return sync_group_to_emails("alumni@sib-utrecht.nl", emails, dry_run=dry_run, logger=logger)
    elif group == "members":
        logger.info("Syncing members emails:")
        members = list_relations_active_members()

        today = datetime.now(tz=timezone.utc).astimezone().isoformat()[:10]  # YYYY-MM-DD

        prev_members_length = len(members)
        
        # Filter to exclude people who aren't members yet, since this mailing
        # list is mostly for formal e-mails, like GMA convocations.
        members = [m for m in members if m.get("membership_start", "1970-01-01") <= today]

        next_members_length = len(members)

        logger.info(f"Excluding {prev_members_length - next_members_length} members who aren't members yet (by their Conscribo membership_start field).")

        emails = set(a.get("email") for a in members) - {"", None}
        return sync_group_to_emails("members@sib-utrecht.nl", emails, dry_run=dry_run, logger=logger)
    else:
        raise ValueError(f"Unknown group: {group}")
