import argparse
from argparse import ArgumentParser, Namespace

def handle_list(args: Namespace):
    """
    Handle the list command based on the provided arguments.
    This function will be called when the list command is executed.
    """
    if args.dest == "cognito":
        from .sync.conscribo_to_cognito import sync_conscribo_to_cognito
        sync_conscribo_to_cognito(dry_run=args.dry_run)
        return
    
    if args.dest == "laposta":
        from .sync.conscribo_to_laposta import sync_conscribo_to_laposta
        sync_conscribo_to_laposta(dry_run=args.dry_run)
        return
    
    raise ValueError(f"Unknown destination: {args.dest}")

def add_parse_cognito_group(parser: ArgumentParser):
    def handle_cognito_group(args: Namespace):
        pass

    parser.add_argument(
        "cognito-group-id",
        type=str,
        help="The ID of the Cognito group to list members from."
    )
    parser.set_defaults(func=handle_cognito_group)

def add_parse_conscribo_group(parser: ArgumentParser):
    def handle_conscribo_group(args: Namespace):
        from .conscribo.list_relations import get_group_members

        group_id = args.conscribo_group_id
        members = get_group_members(group_id)
        for member in members:
            print(f" - {member}")

    parser.add_argument(
        "conscribo-group-id",
        type=str,
        help="The ID of the Conscribo group to list members from."
    )
    parser.set_defaults(func=handle_conscribo_group)

def add_parse_args(parser: ArgumentParser):
    parser.set_defaults(func=lambda args: parser.print_help())
    # parser.add_argument(
    #     "service",
    #     type=str,
    #     choices=["cognito-group"],
    #     help="What service to list members from.",
    # )

    subparser = parser.add_subparsers(
        description="What service to list members from",
        dest="service"
    )

    add_parse_cognito_group(
        subparser.add_parser(
            "cognito-group",
            help="List members from a Cognito group.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    )

    add_parse_conscribo_group(
        subparser.add_parser(
            "conscribo-group",
            help="List members from a Conscribo group.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    )

    return parser
