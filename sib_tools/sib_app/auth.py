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

sib_app_api_key = None


def prompt_credentials():
    password = getpass(f"API-key for sib_app: ")

    keyring.set_password("sib_app", "api-key", password)

def authenticate() -> str:
    global sib_app_api_key

    # Try environment variable first
    sib_app_api_key = os.environ.get("SIB_APP_API_KEY")
    if sib_app_api_key:
        return sib_app_api_key

    sib_app_api_key = keyring.get_password("sib_app", "api-key")

    if sib_app_api_key is None:
        prompt_credentials()
        return authenticate()
    
    print(f"sib_app API key length: {len(sib_app_api_key)}")

    return sib_app_api_key

def get_sib_app_api_key() -> str:
    global sib_app_api_key

    if sib_app_api_key is None:
        return authenticate()

    return sib_app_api_key


def sib_app_get(url : str, parameters = None) -> dict:
    api_key = get_sib_app_api_key()

    if parameters is not None:
        parameters = urllib.parse.urlencode(parameters)
        url += "?" + parameters

    response = requests.get(
        f"{api_url.removesuffix('/')}/{url.removeprefix('/')}",
        headers={
            "Accept": "application/json",
            "Authorization": f"ApiKey {api_key}"
        },
    )
    response.raise_for_status()

    return response.json()

def sib_app_post(url : str, body : dict[str, Any]) -> dict[str, Any]:
    api_key = get_sib_app_api_key()

    # Flatten body, we need keys like 'custom_fields[prefs][]=optionA'

    response = requests.post(
        f"{api_url}/{url.removeprefix('/')}",
        headers={
            "Accept": "application/json",
            "Authorization": f"ApiKey {api_key}"
        },
        json=body,
    )
    response.raise_for_status()

    return response.json()

def sib_app_delete(url : str) -> dict:
    api_key = get_sib_app_api_key()

    response = requests.delete(
        f"{api_url}/{url.removeprefix('/')}",
        headers={
            "Accept": "application/json",
            "Authorization": f"ApiKey {api_key}"
        },
    )
    response.raise_for_status()

    return response.json()

def sib_app_put(url : str, body : dict[str, Any]) -> dict[str, Any]:
    api_key = get_sib_app_api_key()

    response = requests.put(
        f"{api_url}/{url.removeprefix('/')}",
        headers={
            "Accept": "application/json",
            "Authorization": f"ApiKey {api_key}"
        },
        json=body,
    )
    response.raise_for_status()

    return response.json()

def check_available():
    return keyring.get_password("sib_app", "api-key")

def signout():
    try:
        keyring.delete_password("sib_app", "api-key")
    except keyring.errors.PasswordDeleteError:
        pass







