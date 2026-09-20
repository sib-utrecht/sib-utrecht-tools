from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, _SubParsersAction

def add_parse_args(parser: "_SubParsersAction[ArgumentParser]") -> None:
    from .email_handler import add_parse_args as add_email_args
    email_parser = parser.add_parser(
        "handle-email",
        help="Handle an incoming .eml file and process its contents."
    )
    add_email_args(email_parser)
