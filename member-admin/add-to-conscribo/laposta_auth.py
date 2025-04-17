import keyring.credentials
import requests
import json
import keyring
from getpass import getpass
import urllib.parse

# https://api.laposta.nl/doc/index.nl.php

api_url = "https://api.laposta.nl/"

laposta_api_key = None


def prompt_credentials():
    password = getpass(f"API-key for LaPosta: ")

    keyring.set_password("laposta", "api-key", password)

def authenticate() -> str:
    global laposta_api_key

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
        f"{api_url}/{url.removeprefix('/')}",
        auth=(
            api_key,
            ""
        ),
    )
    return response.json()

def laposta_post(url : str, body : dict[str]) -> dict[str]:
    api_key = get_laposta_api_key()

    body_url_encoded = urllib.parse.urlencode(body)
    response = requests.post(
        f"{api_url}/{url.removeprefix('/')}",
        auth=(
            api_key,
            ""
        ),
        data=body_url_encoded,
    )

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

def laposta_patch(url : str, body : dict[str]) -> dict[str]:
    api_key = get_laposta_api_key()

    body_url_encoded = urllib.parse.urlencode(body)
    response = requests.patch(
        f"{api_url}/{url.removeprefix('/')}",
        auth=(
            api_key,
            ""
        ),
        data=body_url_encoded,
    )
    return response.json()







