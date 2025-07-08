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

# Set format to use timestamp
logging.basicConfig(filename="laposta_sync.log", level=logging.DEBUG,
                    format="[%(asctime)s] %(levelname)s: %(message)s")

# Only print INFO and above to stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
# console_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
logging.getLogger().addHandler(console_handler)


def match_laposta_with_conscribo(
    laposta_members, members, alumni
) -> list[tuple[dict, dict, dict]]:
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

            if is_valid_member:
                print(
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
            if is_valid_alumnus:
                print(
                    f"Found alumnus by date of birth: {email} -> {conscribo_alumnus['email']}"
                )
                unmatched_conscribo.discard(conscribo_alumnus.get("email", ""))

            if not is_valid_alumnus:
                conscribo_alumnus = None

        member["conscribo_member"] = conscribo_member
        member["conscribo_alumnus"] = conscribo_alumnus

        entries.append((member, conscribo_member, conscribo_alumnus))

    for email in unmatched_conscribo:
        conscribo_member = members_by_email.get(email, None)
        conscribo_alumnus = alumni_by_email.get(email, None)

        if conscribo_member is not None:
            print(f"Conscribo member not found in Laposta: {email}")
        elif conscribo_alumnus is not None:
            print(f"Conscribo alumnus not found in Laposta: {email}")
        else:
            print(f"Conscribo relation not found for email: {email}")

        entries.append((None, conscribo_member, conscribo_alumnus))

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


def sync_conscribo_to_laposta(dry_run=True):
    laposta_members = get_aggregated_relations()

    # Override dry_run for testing purposes
    # dry_run = True
    print(f"Member count: {len(laposta_members)}")
    assert len(laposta_members) > 5, "No members found in Laposta."

    # print(json.dumps(laposta_members[:5], default=str, indent=2))

    block_email_members = get_block_email_members()

    print(f"Block email members: {json.dumps(list(block_email_members))}")

    members = list_relations_active_members()
    alumni = list_relations_active_alumni()
    print(f"Conscribo members count: {len(members)}")
    print(f"Conscribo alumni count: {len(alumni)}")

    # No need to filter members or alumni here, already filtered by abstraction

    entries = match_laposta_with_conscribo(laposta_members, members, alumni)

    # print(f"First 5 entries:")
    # for entry in entries[:5]:
    #     print(json.dumps(entry, indent=2, default=str))

    current_and_desired: list[tuple[dict, dict]] = []

    now = datetime.now().isoformat()
    logging.info(f"Sync started at {now}")

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
            logging.warning(
                f"Skipping entry with conscribo_id 'ignore': {json.dumps([email, first_name, last_name])}"
            )
            continue

        if email is None or len(email) == 0:
            logging.warning(
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
        # print(
        #     f"For {email}: {block_all=}, {is_member=}, {is_alumnus=}, {date_of_birth=}, desired={json.dumps(desired)}"
        # )

        current_and_desired.append((laposta_member, desired))

    # print(json.dumps(current_and_desired, indent=2, default=str))
    # exit(0)


    key_to_laposta = get_key_to_laposta()

    for entry in current_and_desired:
        laposta_member, desired = entry

        # if desired.get("first_name", None) != "XXX":
        #     continue


        # print(f"Current: {json.dumps(laposta_member)}")
        # print(f"Desired: {json.dumps(desired)}")
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
            logging.warning(
                f"Warning: Inconsistent names or date of birth for {laposta_member['email']}:"
            )
            logging.warning(
                f"  Current: {laposta_member.get('first_name', '')} {laposta_member.get('last_name', '')} ({laposta_member.get('date_of_birth', '')})"
            )
            logging.warning(
                f"  Desired: {desired.get('first_name', '')} {desired.get('last_name', '')} ({desired.get('date_of_birth', '')})"
            )
            force_readd = True
            # continue

        if current_lists == desired_lists and not force_readd:
            continue

        conscribo_id = desired.get("conscribo_id", None)

        basic_info = (
            f"{current_flags} -> {desired_flags}",
            desired["first_name"],
            desired["last_name"],
            desired["email"],
        )

        logging.info(f"UPDATE {conscribo_id} {json.dumps(basic_info)}")

        # print(
        #     f"Updating {desired['email']}: {current_flags} -> {desired_flags}, "
        #     f"lists: {current_lists} -> {desired_lists}"
        # )
        # print(f"Desired: {json.dumps(desired)}")


        # print(json.dumps(laposta_member))

        # if dry_run:
        #     continue

        add_lists = set(desired_lists) - set(current_lists)
        remove_lists = set(current_lists) - set(desired_lists)

        if force_readd:
            remove_lists = set(current_lists)
            add_lists = set(desired_lists)


        for list_id in remove_lists:
            logging.info(f"  Removing {desired['email']} from list {list_id}")
            member_id = laposta_member["laposta_member_ids"].get(list_id, None)
            # logging.debug(f"  Member ID for list {list_id}: {member_id}")

            if member_id is None:
                logging.error(
                    f"  Member ID for list {list_id} not found for {desired['email']}. Skipping removal."
                )
                continue

            
            url = f"/v2/member/{member_id}?list_id={list_id}"
            logging.debug(f"  Doing DELETE to Laposta: {url}")

            if dry_run:
                logging.debug("Dry run, not executing")
                continue

            response = auth.laposta_delete(
                url
            )
            logging.debug(f"Response: {json.dumps(response)}")
            sleep(2)


        for list_id in add_lists:
            logging.info(f"  Adding {desired['email']} to list {list_id}")
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


            # if desired.get("first_name", None) != "XXXX":
            #     continue

            logging.debug(f"  Doing POST to Laposta: {json.dumps(payload, indent=2)}")

            if dry_run:
                logging.debug("Dry run, not executing")
                continue

            response = auth.laposta_post(
                f"/v2/member",
                payload,
            )

            logging.debug(f"Response: {json.dumps(response)}")
            sleep(2)
