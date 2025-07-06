import argparse
from argparse import ArgumentParser, Namespace
import sys
from sib_tools.conscribo.relations import list_relations_alumnus
import json

def handle_list(args: Namespace):
    """
    Handle the list command based on the provided arguments.
    This function will be called when the list command is executed.
    """
    if args.resource == "conscribo-alumnus":
        alumni = list_relations_alumnus()
        if args.conscribo_id:
            filtered = [a for a in alumni if str(a.get("conscribo_id")) == str(args.conscribo_id)]
            print(json.dumps(filtered, indent=2))
            
        else:
            print(json.dumps(alumni, indent=2))
            print()
        return
    raise ValueError(f"Unknown resource: {args.dest}")

def add_parse_args(parser: ArgumentParser):
    parser.set_defaults(func=lambda args: parser.print_help())
    subparser = parser.add_subparsers(
        description="What resource to list members from",
        dest="resource"
    )
    alumnus_parser = subparser.add_parser("conscribo-alumnus", help="List Conscribo alumni")
    alumnus_parser.add_argument("--conscribo-id", type=str, required=False, help="Conscribo ID of the alumnus to query")
    alumnus_parser.set_defaults(func=handle_list)
    return parser
