def add_parse_args(parser):
    from .email_handler import add_parse_args as add_email_args
    email_parser = parser.add_parser(
        "handle-email",
        help="Handle an incoming .eml file and process its contents."
    )
    add_email_args(email_parser)
