import sys
from .forms_extract_mail import extract_fields_from_mail, form_to_canonical
import json

def handle_incoming_email(args):
    eml_path = args.eml_path
    try:
        fields = extract_fields_from_mail(eml_path)
        canonical = form_to_canonical(fields)
        print(json.dumps(canonical, indent=2))
    except Exception as e:
        print(f"Failed to process email: {e}", file=sys.stderr)
        sys.exit(1)

def add_parse_args(parser):
    parser.add_argument("eml_path", help="Path to the .eml file to process")
    parser.set_defaults(func=handle_incoming_email)
