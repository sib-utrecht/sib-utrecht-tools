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
    if args.healthcheck == "conscribo-basic":
        from .conscribo.check_basic import check_basic
        check_basic()
        return
    if args.healthcheck == "conscribo-addresses":
        from .conscribo.check_address import check_addresses
        check_addresses(
            include_alumni=args.include_alumni or args.only_alumni,
            include_members=not args.only_alumni
        )
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

    conscribo_basic_parser = subparser.add_parser(
        "conscribo-basic",
        help="Basic Conscribo health check (required fields, etc)."
    )
    conscribo_basic_parser.set_defaults(func=handle_check)

    conscribo_addresses_parser = subparser.add_parser(
        "conscribo-addresses",
        help="Check Conscribo addresses (validity, completeness, etc)."
    )
    conscribo_addresses_parser.set_defaults(func=handle_check)
    conscribo_addresses_parser.add_argument(
        '--include-alumni',
        action='store_true',
        help='Include alumni in the address check'
    )
    conscribo_addresses_parser.add_argument(
        '--only-alumni',
        action='store_true',
        help='Only check alumni addresses (exclude members)'
    )
    return parser
