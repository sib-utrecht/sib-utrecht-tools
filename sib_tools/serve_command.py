from argparse import ArgumentParser, Namespace

from argparse import ArgumentParser, Namespace

def handle_listen_email(args: Namespace) -> None:
    from .listen_sns_for_email import run_email_listener

    run_email_listener()

def add_parse_args(serve_parser: ArgumentParser) -> None:
    serve_subparsers = serve_parser.add_subparsers(dest="serve_command")
    serve_subparsers.required = True
    serve_listen_email_parser = serve_subparsers.add_parser(
        "listen-email",
        help="Start a Flask server to listen for incoming e-mail via SNS webhook.",
    )
    serve_listen_email_parser.set_defaults(func=handle_listen_email)