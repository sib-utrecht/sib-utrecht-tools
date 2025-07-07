import argparse
from argparse import ArgumentParser, Namespace
import json

def add_parse_conscribo_query(parser: ArgumentParser):
    def handle_conscribo_query(args: Namespace):
        from .conscribo.auth import conscribo_get, conscribo_post

        if args.method == "get":
            ans = conscribo_get(args.path)
            print(json.dumps(ans, indent=2))

        if args.method == "post":
            if not args.json:
                print("JSON data is required for POST requests.")
                return
            ans = conscribo_post(args.path, args.json)
            print(json.dumps(ans, indent=2))

    parser.add_argument(
        "method",
        type=str,
        choices=["get", "post"],
        help="The HTTP method to perform."
    )
    parser.add_argument(
        "path",
        type=str,
        help="The path to query."
    )
    parser.add_argument(
        "--json",
        type=json.loads,
        help="JSON data to include in the request body."
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
