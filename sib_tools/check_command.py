import argparse
from argparse import ArgumentParser, Namespace
import logging


def handle_check(args: Namespace):
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('s3transfer').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


    if args.healthcheck == "conscribo-numbering":
        from .conscribo.check_numbering import check_numbering
        check_numbering()
        return
    raise ValueError(f"Unknown health check: {args.healthcheck}")


def add_parse_args(parser: ArgumentParser):
    parser.set_defaults(func=lambda args: parser.print_help())
    subparser = parser.add_subparsers(
        description="Health check to perform",
        dest="healthcheck"
    )

    conscribo_parser = subparser.add_parser(
        "conscribo-numbering",
        help="Check Conscribo member/external numbering consistency."
    )
    conscribo_parser.set_defaults(func=handle_check)
    return parser
