import argparse
from argparse import ArgumentParser, Namespace


def handle_sync(args: Namespace):
    """
    Handle the sync command based on the provided arguments.
    This function will be called when the sync command is executed.
    """
    if args.dest == "cognito":
        from .sync.conscribo_to_cognito import sync_conscribo_to_cognito

        sync_conscribo_to_cognito(dry_run=args.dry_run)
        return

    if args.dest == "laposta":
        from .sync.conscribo_to_laposta import sync_conscribo_to_laposta

        sync_conscribo_to_laposta(dry_run=args.dry_run)
        return

    if args.dest == "cognito-groups":
        from .sync.conscribo_to_cognito_groups import sync_conscribo_to_cognito_groups

        sync_conscribo_to_cognito_groups(dry_run=args.dry_run)
        return

    raise ValueError(f"Unknown destination: {args.dest}")


def add_parse_args(parser: ArgumentParser):
    parser.set_defaults(func=handle_sync)
    parser.add_argument(
        "dest",
        type=str,
        choices=["cognito", "laposta", "cognito-groups"],
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
    return parser
