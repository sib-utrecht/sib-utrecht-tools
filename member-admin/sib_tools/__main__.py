import argparse
from argparse import ArgumentParser
from . import sync_command
from .command_exception import CommandException

def main(args=None):
    parser = ArgumentParser(
        prog="sib-tools",
        description="Tools for member administration, made for SIB-Utrecht."
    )
    parser.set_defaults(func=lambda args: parser.print_help())

    subparser = parser.add_subparsers(
        title="Commands",
        description="Available commands",
        dest="command"
    )

    sync_command.add_parse_args(
        subparser.add_parser(
            "sync",
            help="Synchronize members to other services (e.g. Laposta, or website accounts).",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    )

    args = parser.parse_args(args=args)
    try:
        args.func(args)
    except CommandException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
