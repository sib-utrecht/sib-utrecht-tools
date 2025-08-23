import argparse
from argparse import ArgumentParser, Namespace
import logging
import sys
import io

from sib_tools.utils import print_change_count
from .check_command import mail_results, log_to_html

def handle_sync(args: Namespace):
    """
    Handle the sync command based on the provided arguments.
    This function will be called when the sync command is executed.
    """
    # Reuse logger setup style from check_command
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger("sib_tools_sync")
    logger.setLevel(logging.DEBUG)

    # File output
    file_handler = logging.FileHandler("sib_tools_sync.log")
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    # Avoid duplicate handlers when called multiple times
    if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == file_handler.baseFilename for h in logger.handlers):
        logger.addHandler(file_handler)

    # Stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    if not any(isinstance(h, logging.StreamHandler) and getattr(h, 'stream', None) is sys.stdout for h in logger.handlers):
        logger.addHandler(stream_handler)

    # In-memory capture for mailing
    log_stream = io.StringIO()
    memory_handler = logging.StreamHandler(log_stream)
    memory_handler.setFormatter(logging.Formatter("%(message)s"))
    memory_handler.setLevel(logging.INFO)
    logger.addHandler(memory_handler)

    logger.info(f"Running sync: dest={args.dest}, dry_run={getattr(args, 'dry_run', False)}")

    change_count = 0
    try:
        if args.dest == "all":
            # Run all syncs and sum their change counts
            from .sync.conscribo_to_cognito import sync_conscribo_to_cognito
            from .sync.conscribo_to_laposta import sync_conscribo_to_laposta
            from .sync.conscribo_to_cognito_groups import sync_conscribo_to_cognito_groups
            from .sync.cognito_to_conscribo_groups import sync_cognito_to_conscribo_groups
            from .sync.conscribo_to_google_contacts import sync_conscribo_to_google_contacts
            from .sync.conscribo_to_google_groups import sync_conscribo_to_google_groups

            total = 0
            total += sync_conscribo_to_cognito(dry_run=args.dry_run, logger=logger)
            total += sync_conscribo_to_laposta(dry_run=args.dry_run, logger=logger)
            total += sync_conscribo_to_cognito_groups(dry_run=args.dry_run, logger=logger)
            total += sync_conscribo_to_google_contacts(dry_run=args.dry_run, logger=logger)
            # Run both alumni and members for Google Groups
            total += sync_conscribo_to_google_groups(dry_run=args.dry_run, group="alumni", logger=logger)
            total += sync_conscribo_to_google_groups(dry_run=args.dry_run, group="members", logger=logger)

            print_change_count(total, logger)

            change_count = total
            return

        if args.dest == "cognito":
            from .sync.conscribo_to_cognito import sync_conscribo_to_cognito

            change_count = sync_conscribo_to_cognito(dry_run=args.dry_run, logger=logger)
            return

        if args.dest == "laposta":
            from .sync.conscribo_to_laposta import sync_conscribo_to_laposta

            change_count = sync_conscribo_to_laposta(dry_run=args.dry_run, logger=logger)
            return

        if args.dest == "cognito-groups":
            from .sync.conscribo_to_cognito_groups import sync_conscribo_to_cognito_groups

            change_count = sync_conscribo_to_cognito_groups(dry_run=args.dry_run, logger=logger)
            return

        if args.dest == "cognito-groups-to-conscribo":
            from .sync.cognito_to_conscribo_groups import sync_cognito_to_conscribo_groups

            change_count = sync_cognito_to_conscribo_groups(dry_run=args.dry_run, logger=logger)
            return

        if args.dest == "google-groups":
            from .sync.conscribo_to_google_groups import sync_conscribo_to_google_groups

            change_count = sync_conscribo_to_google_groups(
                dry_run=args.dry_run, group=getattr(args, "group", "alumni"), logger=logger
            )
            return

        if args.dest == "google-contacts":
            from .sync.conscribo_to_google_contacts import sync_conscribo_to_google_contacts

            # Only consider contacts with label 'Member'
            change_count = sync_conscribo_to_google_contacts(dry_run=args.dry_run, logger=logger)
            return

        if args.dest == "conscribo-list":
            from .sync.sync_conscribo_to_conscribo_list import sync_active_members_to_group, sync_active_alumni_to_group

            group_id = getattr(args, "group_id", None)
            if group_id is None:
                raise ValueError("group_id is required for conscribo-list destination")
            
            member_type = getattr(args, "member_type", "members")
            if member_type == "members":
                change_count = sync_active_members_to_group(group_id, dry_run=args.dry_run, logger=logger)
            elif member_type == "alumni":
                change_count = sync_active_alumni_to_group(group_id, dry_run=args.dry_run, logger=logger)
            else:
                raise ValueError(f"Unknown member_type: {member_type}")
            return

        raise ValueError(f"Unknown destination: {args.dest}")
    finally:
        logger.info("")

        # Prepare and optionally mail results
        logger.removeHandler(memory_handler)
        if getattr(args, "mail_output", False) and change_count:
            html = log_to_html(log_stream.getvalue(), dark_mode=False, is_sync=True)
            subject = f"Synced {change_count} changes in member administration"
            mail_results(html, subject=subject, logger=logger)


def add_parse_args(parser: ArgumentParser):
    parser.set_defaults(func=handle_sync)
    parser.add_argument(
        "dest",
        type=str,
        choices=[
            "all",
            "cognito",
            "laposta",
            "cognito-groups",
            "cognito-groups-to-conscribo",
            "google-groups",
            "google-contacts",
            "conscribo-list",
        ],
        help="Destination service to sync members to.",
    )

    # parser.add_argument(
    #     "--file",
    #     "-f",
    #     type=str,
    #     required=True,
    #     help="Path to the CSV file containing members to add.",
    # )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, will not actually add members, just print what would be done.",
    )
    parser.add_argument(
        "--group",
        choices=["members", "alumni"],
        default="alumni",
        help="(Only applies to 'google-groups') Which group to sync: 'members' or 'alumni' (default: alumni)",
    )
    parser.add_argument(
        "--group-id",
        type=int,
        default=53,
        help="(Required for 'conscribo-list') The ID of the Conscribo group to sync to",
    )
    parser.add_argument(
        "--member-type",
        choices=["members", "alumni"],
        default="members",
        help="(Only applies to 'conscribo-list') Which member type to sync: 'members' or 'alumni' (default: members)",
    )
    parser.add_argument(
        "--mail-output",
        action="store_true",
        help="Mail the HTML log output via AWS SES to the default recipient",
    )
    return parser
