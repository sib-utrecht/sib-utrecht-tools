import argparse
from argparse import ArgumentParser
from .auth import configure_keyring
configure_keyring()

from . import (
    sync_command,
    list_command,
    api_command,
    check_command,
    email,
    serve_command,
)
from .command_exception import CommandException
import os
import keyring


def main(args=None):
    parser = ArgumentParser(
        prog="sib-tools",
        description="Tools for member administration, made for SIB-Utrecht.",
    )
    parser.set_defaults(func=lambda args: parser.print_help())

    subparser = parser.add_subparsers(
        title="Commands", description="Available commands", dest="command"
    )

    sync_command.add_parse_args(
        subparser.add_parser(
            "sync",
            help="Synchronize members to other services (e.g. Laposta, or website accounts).",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
    )

    list_command.add_parse_args(subparser.add_parser("list", help="List information"))

    api_command.add_parse_args(
        subparser.add_parser(
            "api", help="Issue a raw API command (e.g. 'GET /relations/groups/')"
        )
    )

    check_command.add_parse_args(
        subparser.add_parser("check", help="Check data consistency and integrity.")
    )

    email.add_parse_args(subparser)

    serve_command.add_parse_args(
        subparser.add_parser(
            "serve", help="Run server endpoints (e.g. for SNS webhooks)"
        )
    )

    args = parser.parse_args(args=args)
    try:
        args.func(args)
    except CommandException as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
