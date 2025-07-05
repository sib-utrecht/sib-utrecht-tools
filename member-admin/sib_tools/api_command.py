import argparse
from argparse import ArgumentParser, Namespace
import json

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

def add_parse_conscribo_query(parser: ArgumentParser):
    def handle_conscribo_query(args: Namespace):
        from .conscribo.conscribo_auth import conscribo_get, conscribo_post

        if args.method == "GET":
            ans = conscribo_get(args.path)
            print(json.dumps(ans, indent=2))

    parser.add_argument(
        "method",
        type=str,
        choices=["GET"],
        help="The HTTP method to perform."
    )
    parser.add_argument(
        "path",
        type=str,
        help="The path to query."
    )

    parser.set_defaults(func=handle_conscribo_query)

def add_parse_args(parser: ArgumentParser):
    parser.set_defaults(func=lambda args: parser.print_help())
    # parser.add_argument(
    #     "service",
    #     type=str,
    #     choices=["cognito-group"],
    #     help="What service to list members from.",
    # )

    subparser = parser.add_subparsers(
        description="What service to query",
        dest="service"
    )

    add_parse_conscribo_query(
        subparser.add_parser(
            "conscribo",
            help="Perform an Conscribo API query.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    )

    return parser
