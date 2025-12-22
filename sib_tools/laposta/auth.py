import os
from .constants import api_url
import requests
import json
import keyring
import keyring.errors
from getpass import getpass
import urllib.parse
from dotenv import load_dotenv
from typing import Any

load_dotenv()

laposta_api_key = None


def prompt_credentials():
    password = getpass(f"API-key for LaPosta: ")

    keyring.set_password("laposta", "api-key", password)

def authenticate() -> str:
    global laposta_api_key

    # Try environment variable first
    laposta_api_key = os.environ.get("LAPOSTA_API_KEY")
    if laposta_api_key:
        return laposta_api_key

    laposta_api_key = keyring.get_password("laposta", "api-key")

    if laposta_api_key is None:
        prompt_credentials()
        return authenticate()
    
    print(f"Laposta API key length: {len(laposta_api_key)}")

    return laposta_api_key

def get_laposta_api_key() -> str:
    global laposta_api_key

    if laposta_api_key is None:
        return authenticate()

    return laposta_api_key


def laposta_get(url : str, parameters = None) -> dict:
    api_key = get_laposta_api_key()

    if parameters is not None:
        parameters = urllib.parse.urlencode(parameters)
        url += "?" + parameters

    response = requests.get(
        f"{api_url.removesuffix('/')}/{url.removeprefix('/')}",
        auth=(
            api_key,
            ""
        ),
    )
    return response.json()

def make_form_flattened(body : dict[str, Any]) -> dict[str, Any]:
    """
    Converts a dictionary to a flattened form suitable for form submission.
    For example, {'custom_fields': {'prefs': ['optionA', 'optionB']}}
    becomes {'custom_fields[prefs][]=optionA', 'custom_fields[prefs][]=optionB'}.
    """
    body_flat = {}

    def insert_value(key, value):
        nonlocal body_flat

        if isinstance(value, list):
            for item in value:
                insert_value(f"{key}[]", item)
            return

        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                insert_value(f"{key}[{sub_key}]", sub_value)
            return

        body_flat[key] = value

    for key, value in body.items():
        insert_value(key, value)
    return body_flat


def laposta_post(url : str, body : dict[str, Any]) -> dict[str, Any]:
    api_key = get_laposta_api_key()

    # Flatten body, we need keys like 'custom_fields[prefs][]=optionA'
    body_flat = make_form_flattened(body)
    print("Flattened body for POST:", json.dumps(body_flat, indent=2))

    response = requests.post(
        f"{api_url}/{url.removeprefix('/')}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        auth=(
            api_key,
            ""
        ),
        data=body_flat,
    )
    return response.json()

def laposta_delete(url : str) -> dict:
    api_key = get_laposta_api_key()

    response = requests.delete(
        f"{api_url}/{url.removeprefix('/')}",
        auth=(
            api_key,
            ""
        ),
    )
    return response.json()

def laposta_patch(url : str, body : dict[str, Any]) -> dict[str, Any]:
    api_key = get_laposta_api_key()

    response = requests.patch(
        f"{api_url}/{url.removeprefix('/')}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        auth=(
            api_key,
            ""
        ),
        data=body,
    )
    return response.json()

def check_available():
    return keyring.get_password("laposta", "api-key")

def show():
    """Display Laposta credentials information with redacted API key."""
    def redact_key(key):
        return "****"
        # if not key or len(key) < 8:
        #     return "****"
        # return key[:4] + "*" * (len(key) - 8) + key[-4:]
    
    api_key = os.environ.get("LAPOSTA_API_KEY") or keyring.get_password("laposta", "api-key")
    
    print("\n=== Laposta Credentials ===")
    print(f"API URL: {api_url}")
    
    if api_key:
        print(f"API Key: {redact_key(api_key)}")
        print(f"Source: {'Environment Variable' if os.environ.get('LAPOSTA_API_KEY') else 'Keyring'}")
    else:
        print("API Key: Not set")
    print()

def signout():
    try:
        keyring.delete_password("laposta", "api-key")
    except keyring.errors.PasswordDeleteError:
        pass







