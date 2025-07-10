import argparse
from argparse import ArgumentParser, Namespace
import logging
import sys
import io
from html import escape
import re
import importlib
from datetime import datetime, timezone

def mail_results(
    contents: str,
    subject: str = "Health check report by sib-tools",
    logger: logging.Logger = None,
):
    """
    Mail the results using AWS SES.
    This function is a placeholder and should be implemented with actual mailing logic.
    """
    import boto3
    from .aws.auth import get_ses_client
    from .cognito import auth as cognito_auth

    if logger is None:
        logger = logging.getLogger()

    ses_client = get_ses_client()
    ses_client.send_email(
        Source="member-admin-bot@sib-utrecht.nl",
        Destination={"ToAddresses": ["secretaris@sib-utrecht.nl"]},
        Message={"Subject": {"Data": subject}, "Body": {"Html": {"Data": contents}}},
    )
    logger.info("Mailed results via AWS SES to secretaris@sib-utrecht.nl.")


def handle_check(args: Namespace):
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger("sib_tools_check")
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler("sib_tools_check.log")
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
    )
    logger.addHandler(file_handler)
    stream_handler = logging.StreamHandler(sys.stdout)
    if getattr(args, "print_timestamps", False):
        stream_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
    logger.addHandler(stream_handler)

    log_stream = io.StringIO()
    memory_handler = logging.StreamHandler(log_stream)
    if getattr(args, "print_timestamps", False):
        memory_handler.setFormatter(
            logging.Formatter("\x1b[90m[%(asctime)s]\x1b[0m %(message)s")
        )
    else:
        memory_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(memory_handler)

    logger.info(f"\x1b[90mRunning health check: {args.healthcheck}\x1b[0m")
    logger.info(
        f"\x1b[90mCurrent time: {datetime.now().astimezone().isoformat().replace('T', ' ').replace('+', ' | Timezone: UTC+')}\x1b[0m"
    )
    logger.info(f"\x1b[90mCommand arguments: {args}\x1b[0m")
    logger.info("")
    try:
        if args.healthcheck == "selftest":
            check_selftest(logger)
        elif args.healthcheck == "conscribo-numbering":
            from .conscribo.check_numbering import check_numbering

            check_numbering(logger)
        elif args.healthcheck == "conscribo-basic":
            from .conscribo.check_basic import check_basic

            check_basic(logger)
        elif args.healthcheck == "conscribo-addresses":
            from .conscribo.check_address import check_addresses

            check_addresses(
                logger,
                include_alumni=args.include_alumni or args.only_alumni,
                include_members=not args.only_alumni,
            )
        else:
            raise ValueError(f"Unknown health check: {args.healthcheck}")
    finally:
        logger.info("")
        logger.info(
            f"\x1b[90mFinished at: {datetime.now().astimezone().isoformat().replace('T', ' ').replace('+', ' | Timezone: UTC+')}\x1b[0m"
        )
        logger.removeHandler(memory_handler)


    if args.output_to_html or args.mail_output:
        log_contents = log_stream.getvalue()
        dark_mode = getattr(args, "html_dark_mode", False)
        html = log_to_html(log_contents, dark_mode)
        if args.output_to_html:
            with open(args.output_to_html, "w", encoding="utf-8") as f:
                f.write(html)
        if args.mail_output:
            mail_results(
                html,
                subject=f"Health check report by sib-tools ({args.healthcheck})",
                logger=logger,
            )


def add_parse_args(parser: ArgumentParser):
    parser.set_defaults(func=lambda args: parser.print_help())
    subparser = parser.add_subparsers(
        description="Health check to perform", dest="healthcheck"
    )

    def create_subparser(name: str, *, help: str) -> ArgumentParser:
        parser = subparser.add_parser(name, help=help)
        parser.set_defaults(func=handle_check)
        parser.add_argument(
            "--output-to-html",
            metavar="FILENAME",
            help="Write log output as HTML to the specified file",
        )
        parser.add_argument(
            "--html-dark-mode",
            action="store_true",
            help="Use dark mode for HTML output (default: light mode)",
        )
        parser.add_argument(
            "--mail-output",
            action="store_true",
            help="Mail the HTML output to info@example.org using AWS SES",
        )
        parser.add_argument(
            "--print-timestamps",
            action="store_true",
            help="Show timestamps in log output (stdout and HTML)",
        )
        return parser

    # Add selftest check
    create_subparser(
        "selftest", help="Show ANSI color palette for self-test and debug."
    )

    conscribo_parser = create_subparser(
        "conscribo-numbering",
        help="Check Conscribo member/external numbering consistency.",
    )

    conscribo_basic_parser = create_subparser(
        "conscribo-basic", help="Basic Conscribo health check (required fields, etc)."
    )

    conscribo_addresses_parser = create_subparser(
        "conscribo-addresses",
        help="Check Conscribo addresses (validity, completeness, etc).",
    )
    conscribo_addresses_parser.add_argument(
        "--include-alumni",
        action="store_true",
        help="Include alumni in the address check",
    )
    conscribo_addresses_parser.add_argument(
        "--only-alumni",
        action="store_true",
        help="Only check alumni addresses (exclude members)",
    )
    return parser


def ansi_to_html(text):
    # Map ANSI color codes to HTML color styles
    ansi_color_map = {
        "30": "color:#000000;",  # Black
        "31": "color:#c00;",  # Red
        "32": "color:#0a0;",  # Green
        "33": "color:#bb0;",  # Yellow
        "34": "color:#00c;",  # Blue
        "35": "color:#a0a;",  # Magenta
        "36": "color:#0aa;",  # Cyan
        "37": "color:#e0e0e0;",  # White (light gray)
        "90": "color:#888;",  # Bright Black (Gray)
        "91": "color:#f55;",  # Bright Red
        "92": "color:#5f5;",  # Bright Green
        "93": "color:#bba800;",  # Bright Yellow (darker)
        "94": "color:#55f;",  # Bright Blue
        "95": "color:#f5f;",  # Bright Magenta
        "96": "color:#5ff;",  # Bright Cyan
        "97": "color:#e0e0e0;",  # Bright White (light gray)
    }
    # Regex to match ANSI escape sequences
    ansi_escape = re.compile(r"\x1b\[([0-9;]+)m")
    # Stack for nested spans
    span_stack = []
    result = ""
    last_end = 0
    for match in ansi_escape.finditer(text):
        start, end = match.span()
        codes = match.group(1).split(";")
        # Add text before this escape
        result += escape(text[last_end:start])
        last_end = end
        # Handle reset
        if "0" in codes:
            while span_stack:
                result += "</span>"
                span_stack.pop()
            continue
        # Handle color codes
        for code in codes:
            style = ansi_color_map.get(code)
            if style:
                result += f'<span style="{style}">'
                span_stack.append("span")
    # Add remaining text
    result += escape(text[last_end:])
    # Close any open spans
    while span_stack:
        result += "</span>"
        span_stack.pop()
    return result


def log_to_html(log_contents: str, dark_mode: bool = False) -> str:
    if dark_mode:
        style = """
            body { background: #222; color: #e0e0e0; }
            .centered-pre {
                background: #181818;
                box-shadow: 0 2px 8px #0008;
                color: #e0e0e0;
            }
        """
    else:
        style = """
            body { background: #fff; color: #222; }
            .centered-pre {   
                background: #f8f8f8;
                box-shadow: 0 2px 8px #0002;
            }
        """

    style += """
        pre.centered-pre {
            max-width: 120ch;
            margin: 40px auto;
            border-radius: 8px;
            padding: 2em;
            font-family: monospace;
            font-size: 1em;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        .banner {
            background: #f3f3f3;
            color: #222;
            padding: 1em 2em;
            text-align: left;
            font-weight: bold;
            border-bottom: 2px solid #bdbdbd;
            font-family: sans-serif;
            border-radius: 0 0 8px 8px;
            margin-bottom: 2em;
        }
        .banner .icon {
            display: inline-block;
            margin-right: 0.25em;
            flex-shrink: 0;
            color: #1976d2;
        }
        .banner .banner-text {
            font-weight: normal;
        }
        """

    banner = """
        <div class="banner">
            <span class="icon" aria-label="info" title="Info">Note.</span>
            <span class="banner-text">This is the output of an automated health check by a script at <a href="https://github.com/sib-utrecht/sib-utrecht-tools" target="_blank" style="color:#1976d2;text-decoration:underline;">https://github.com/sib-utrecht/sib-utrecht-tools</a>. It aims to help you in finding issues, and fixing them. If you are confused, please message the IT committee.</span>
        </div>
        """
    return (
        f"<html><head><style>{style}</style></head><body>"
        f"{banner}"
        '<pre class="centered-pre">' + ansi_to_html(log_contents) + "</pre>"
        "</body></html>"
    )


def check_selftest(logger):
    logger.info("ANSI color palette for review:")
    color_names = [
        ("30", "Black"),
        ("31", "Red"),
        ("32", "Green"),
        ("33", "Yellow"),
        ("34", "Blue"),
        ("35", "Magenta"),
        ("36", "Cyan"),
        ("37", "White"),
        ("90", "Bright Black (Gray)"),
        ("91", "Bright Red"),
        ("92", "Bright Green"),
        ("93", "Bright Yellow"),
        ("94", "Bright Blue"),
        ("95", "Bright Magenta"),
        ("96", "Bright Cyan"),
        ("97", "Bright White"),
    ]
    for code, name in color_names:
        logger.info(f"\x1b[{code}mANSI {code} - {name}\x1b[0m")
    logger.info("End of ANSI color palette.")
