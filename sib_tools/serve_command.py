import argparse
from argparse import ArgumentParser, Namespace
import logging
import sys
import io
from html import escape
import re
import importlib
from datetime import datetime, timezone

def handle_listen_email(args):
    from .serve import run_email_listener

    run_email_listener()

def add_parse_args(serve_parser):
    serve_subparsers = serve_parser.add_subparsers(dest="serve_command")
    serve_subparsers.required = True
    serve_listen_email_parser = serve_subparsers.add_parser(
        "listen-email",
        help="Start a Flask server to listen for incoming e-mail via SNS webhook.",
    )
    serve_listen_email_parser.set_defaults(func=handle_listen_email)