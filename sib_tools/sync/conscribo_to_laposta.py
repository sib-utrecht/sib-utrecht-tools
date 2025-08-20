import boto3
from time import sleep
import json
import logging
import sys

from ..conscribo.relations import (
    list_relations_members,
    list_relations_alumnus,
    list_relations_active_members,
    list_relations_active_alumni,
)
from ..conscribo.groups import get_block_email_members

from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict, get_key_to_laposta, expand_dict
from ..laposta import auth
from ..laposta import list_members
from ..laposta.list_members import get_aggregated_relations
from datetime import datetime
from ..utils import print_change_count, print_header


def match_laposta_with_conscribo(
    laposta_members, members, alumni, logger: logging.Logger | None = None
) -> list[tuple[dict, dict, dict]]:
    logger = logger or logging.getLogger()

    laposta_members_by_email = {
        member.get("email"): member for member in laposta_members
    }
    laposta_members_by_email.pop(None, None)
    laposta_members_by_email.pop("", None)

    members_by_email = {member.get("email"): member for member in members}
    members_by_email.pop(None, None)
    members_by_email.pop("", None)
    members_by_dob = {
        member.get("date_of_birth"): member
        for member in members
        if member.get("date_of_birth")
    }

    alumni_by_email = {alumnus.get("email"): alumnus for alumnus in alumni}
    alumni_by_email.pop(None, None)
    alumni_by_email.pop("", None)
    alumni_by_dob = {
        alumnus.get("date_of_birth"): alumnus
        for alumnus in alumni
        if alumnus.get("date_of_birth")
    }
    

    entries = []

    unmatched_conscribo = (
        set(members_by_email.keys()) | set(alumni_by_email.keys())
    ) - set(laposta_members_by_email.keys())

    for member in laposta_members:
        email = member.get("email")
        date_of_birth = member.get("date_of_birth", None)
        conscribo_member = members_by_email.get(email, None)
        conscribo_alumnus = alumni_by_email.get(email, None)

        if (
            conscribo_member is None
            and conscribo_alumnus is None
            and date_of_birth is not None
        ):
            # If not found, the e-mail address may have changed. Check whether
            # we can match it to someone with the same date of birth and full
            # name.

            conscribo_member = members_by_dob.get(date_of_birth, None)
            is_valid_member = conscribo_member is not None and (
                conscribo_member.get("first_name") == member.get("first_name")
                and conscribo_member.get("last_name") == member.get("last_name")
                # Make sure the email is not already matched
                and laposta_members_by_email.get(conscribo_member.get("email", ""))
                is None
            )

            if is_valid_member and conscribo_member is not None:
                logger.info(
                    f"Found member by date of birth: {email} -> {conscribo_member['email']}"
                )
                unmatched_conscribo.discard(conscribo_member.get("email", ""))

            if not is_valid_member:
                conscribo_member = None

            conscribo_alumnus = alumni_by_dob.get(date_of_birth, None)
            is_valid_alumnus = conscribo_alumnus is not None and (
                conscribo_alumnus.get("first_name") == member.get("first_name")
                and conscribo_alumnus.get("last_name") == member.get("last_name")
                # Make sure the email is not already matched
                and laposta_members_by_email.get(conscribo_alumnus.get("email", ""))
                is None
            )
            if is_valid_alumnus and conscribo_alumnus is not None:
                logger.info(
                    f"Found alumnus by date of birth: {email} -> {conscribo_alumnus['email']}"
                )
                unmatched_conscribo.discard(conscribo_alumnus.get("email", ""))

            if not is_valid_alumnus:
                conscribo_alumnus = None

        member["conscribo_member"] = conscribo_member
        member["conscribo_alumnus"] = conscribo_alumnus

        entries.append((member, conscribo_member, conscribo_alumnus))

    unmatched_members = []
    unmatched_alumni = []

    for email in unmatched_conscribo:
        conscribo_member = members_by_email.get(email, None)
        conscribo_alumnus = alumni_by_email.get(email, None)

        if conscribo_member is not None:
            unmatched_members.append(email)
            # logger.info(f"Conscribo member not found in Laposta: {email}")
        elif conscribo_alumnus is not None:
            unmatched_alumni.append(email)
            # logger.info(f"Conscribo alumnus not found in Laposta: {email}")
        else:
            logger.info(f"Conscribo relation not found for email: {email}")

        entries.append((None, conscribo_member, conscribo_alumnus))

    if unmatched_members:
        logger.debug(f"Unmatched members: {', '.join(unmatched_members)}")

    if unmatched_alumni:
        logger.debug(f"Unmatched alumni: {', '.join(unmatched_alumni)}")

    return entries


def get_participating_lists(member):
    list_ids = []

    if member.get("send_birthday", False):
        list_ids.append(list_members.member_birthday_list_id)

    if member.get("send_newsletter", False):
        list_ids.append(list_members.member_newsletter_list_id)

    if member.get("send_birthday_alumnus", False):
        list_ids.append(list_members.alumni_birthday_list_id)

    return list_ids


def get_participating_flags(member):
    flags = [
        "b" if member.get("send_birthday", False) else "-",
        "n" if member.get("send_newsletter", False) else "-",
        "a" if member.get("send_birthday_alumnus", False) else "-",
    ]
    return "".join(flags)


def sync_conscribo_to_laposta(dry_run=True, logger: logging.Logger | None = None) -> int:
    logger = logger or logging.getLogger(__name__)
    print_header("Syncing Conscribo members to Laposta lists...", logger)
    laposta_members = get_aggregated_relations()

    logger.info("Syncing Conscribo to Laposta...")

    # Override dry_run for testing purposes
    # dry_run = True
    logger.debug(f"Member count: {len(laposta_members)}")
    assert len(laposta_members) > 5, "No members found in Laposta."

    # logger.debug(json.dumps(laposta_members[:5], default=str, indent=2))

    block_email_members = get_block_email_members()

    logger.debug(f"Block email members: {json.dumps(list(block_email_members))}")

    members = list_relations_active_members()
    alumni = list_relations_active_alumni()
    logger.info(f"Conscribo members count: {len(members)}")
    logger.info(f"Conscribo alumni count: {len(alumni)}")

    # No need to filter members or alumni here, already filtered by abstraction

    entries = match_laposta_with_conscribo(laposta_members, members, alumni, logger=logger)

    current_and_desired: list[tuple[dict, dict]] = []

    now = datetime.now().isoformat()
    logger.info(f"Sync started at {now}")

    for entry in entries:
        laposta_member, conscribo_member, conscribo_alumnus = entry

        def resolve_field(name):
            nonlocal conscribo_member, conscribo_alumnus, laposta_member
            values = (
                a.get(name, None)
                for a in (conscribo_member, conscribo_alumnus, laposta_member)
                if a is not None
            )
            return next((v for v in values if v is not None), None)

        email = resolve_field("email")
        first_name = resolve_field("first_name")
        last_name = resolve_field("last_name")
        date_of_birth = resolve_field("date_of_birth")
        conscribo_id = resolve_field("conscribo_id")

        is_member = False
        is_alumnus = False

        block_all = False
        if laposta_member is not None and laposta_member.get("conscribo_id") == "ignore":
            logger.warning(
                f"Skipping entry with conscribo_id 'ignore': {json.dumps([email, first_name, last_name])}"
            )
            continue

        if email is None or len(email) == 0:
            logger.warning(
                f"Skipping entry with no email: {json.dumps([first_name, last_name, (conscribo_member or {}).get('other', {}).get('selector')])}"
            )
            continue

        if conscribo_member is not None:
            if conscribo_member.get("conscribo_id") in block_email_members:
                block_all = True
            membership_end = conscribo_member.get("membership_end", None) or ""

            is_member = len(membership_end) == 0 or membership_end > now

        if conscribo_alumnus is not None:
            if conscribo_alumnus.get("conscribo_id") in block_email_members:
                block_all = True

            deregistered = conscribo_alumnus.get(
                "requested_deregistration_alumnus", False
            )
            is_alumnus = not deregistered

        if laposta_member is None:
            laposta_member = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "date_of_birth": date_of_birth,
                "send_birthday": False,
                "send_newsletter": False,
                "send_birthday_alumnus": False,
            }

        desired = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": date_of_birth,
            "send_birthday": is_member and date_of_birth is not None,
            "send_newsletter": is_member,
            "send_birthday_alumnus": is_alumnus and date_of_birth is not None,
            "conscribo_id": conscribo_id,
        }

        if block_all:
            desired["send_birthday"] = False
            desired["send_newsletter"] = False
            desired["send_birthday_alumnus"] = False
        # logger.debug(
        #     f"For {email}: {block_all=}, {is_member=}, {is_alumnus=}, {date_of_birth=}, desired={json.dumps(desired)}"
        # )

        current_and_desired.append((laposta_member, desired))

    key_to_laposta = get_key_to_laposta()

    change_count = 0

    for entry in current_and_desired:
        laposta_member, desired = entry

        current_flags = get_participating_flags(laposta_member)
        desired_flags = get_participating_flags(desired)

        current_lists = get_participating_lists(laposta_member)
        desired_lists = get_participating_lists(desired)

        first_names = {
            laposta_member.get("first_name", None),
            desired.get("first_name", None),
        } - {None, ""}
        last_names = {
            laposta_member.get("last_name", None),
            desired.get("last_name", None),
        } - {None, ""}
        date_of_births = {
            laposta_member.get("date_of_birth", None),
            desired.get("date_of_birth", None),
        } - {None, ""}

        force_readd = False

        if len(first_names) > 1 or len(last_names) > 1 or len(date_of_births) > 1:
            logger.warning(
                f"Warning: Inconsistent names or date of birth for {laposta_member['email']}:"
            )
            logger.warning(
                f"  Current: {laposta_member.get('first_name', '')} {laposta_member.get('last_name', '')} ({laposta_member.get('date_of_birth', '')})"
            )
            logger.warning(
                f"  Desired: {desired.get('first_name', '')} {desired.get('last_name', '')} ({desired.get('date_of_birth', '')})"
            )
            force_readd = True
            # continue

        if laposta_member.get("email") != desired.get("email"):
            logger.info(f"Updating email {laposta_member.get('email')} to {desired.get('email')}")
            force_readd = True

        if set(current_lists) == set(desired_lists) and not force_readd:
            continue

        # Count changes: removals + additions (force_readd implies full remove+add)
        remove_lists = set(current_lists) - set(desired_lists)
        add_lists = set(desired_lists) - set(current_lists)
        if force_readd:
            remove_lists = set(current_lists)
            add_lists = set(desired_lists)
        change_count += len(remove_lists) + len(add_lists)

        conscribo_id = desired.get("conscribo_id", None)

        basic_info = (
            f"{current_flags} -> {desired_flags}",
            desired["first_name"],
            desired["last_name"],
            desired["email"],
        )

        logger.info(f"UPDATE {conscribo_id} {json.dumps(basic_info)}")

        for list_id in remove_lists:
            logger.info(f"  Removing {laposta_member['email']} from list {list_id}")
            member_id = laposta_member["laposta_member_ids"].get(list_id, None)

            if member_id is None:
                logger.error(
                    f"  Member ID for list {list_id} not found for {laposta_member['email']}. Skipping removal."
                )
                continue

            url = f"/v2/member/{member_id}?list_id={list_id}"
            logger.debug(f"  Doing DELETE to Laposta: {url}")

            if dry_run:
                logger.debug("Dry run, not executing")
                continue

            response = auth.laposta_delete(
                url
            )
            logger.debug(f"Response: {json.dumps(response)}")
            sleep(2)

        for list_id in add_lists:
            logger.info(f"  Adding {desired['email']} to list {list_id}")
            # if list_id == list_members.alumni_birthday_list_id:
            #     continue

            payload = dict()
            for k, v in desired.items():
                translated_key = key_to_laposta.get(k, None)
                if translated_key is None:
                    continue

                payload[translated_key] = v

            payload = expand_dict(payload)
            payload.update(
                {
                    "list_id": list_id,
                    "options": {
                        "upsert": True,
                        "suppress_reactivation": True,
                        "suppress_email_notifications": True,
                    },
                    "ip": "127.0.0.1"
                }
            )

            logger.debug(f"  Doing POST to Laposta: {json.dumps(payload, indent=2)}")

            if dry_run:
                logger.debug("Dry run, not executing")
                continue

            response = auth.laposta_post(
                f"/v2/member",
                payload,
            )

            logger.debug(f"Response: {json.dumps(response)}")
            sleep(2)

    print_change_count(change_count, logger)
    return change_count
