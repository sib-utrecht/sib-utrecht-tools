import os
from dotenv import load_dotenv
load_dotenv()
import keyring.credentials
import requests
import json
import keyring
from getpass import getpass
import urllib.parse
from .constants import relations_doc, api_url

grist_api_key = None

def prompt_credentials():
    password = getpass(f"API-key for Grist: ")

    keyring.set_password("grist", "member-admin-bot", password)

def authenticate() -> str:
    global grist_api_key
    # Try environment variable first
    grist_api_key = os.environ.get("GRIST_API_KEY")
    if grist_api_key:
        return grist_api_key
    grist_api_key = keyring.get_password("grist", "member-admin-bot") or ""

    if len(grist_api_key) == 0:
        prompt_credentials()
        return authenticate()
    
    print(f"Grist API key length: {len(grist_api_key)}")

    return grist_api_key

def get_grist_api_key() -> str:
    global grist_api_key

    if grist_api_key is None:
        return authenticate()

    return grist_api_key

def grist_get(url : str, parameters = None) -> dict:
    api_key = get_grist_api_key()

    if parameters is not None:
        parameters = urllib.parse.urlencode(parameters)
        url += "?" + parameters

    response = requests.get(
        f"{api_url.removesuffix('/')}/{url.removeprefix('/')}",
        headers={
            "Authorization": f"Bearer {api_key}"
        }
    )

    if response.status_code != 200:
        error_msg = None
        try:
            error_msg = response.json().get("error", None)
        except:
            pass
        message = f"Error on GET to Grist route {repr(url)}, got status code {response.status_code}: {repr(error_msg)}"
        print(message)
        print("Response body:")
        print(json.dumps(response.json()))

        raise Exception(message)
    return response.json()

def grist_put(url : str, body : dict | list, query : dict = None) -> dict:
    print(f"Grist: Doing put on {url}")
    
    api_key = get_grist_api_key()

    if query is not None:
        query = urllib.parse.urlencode(query)
        url += "?" + query

    response = requests.put(
        f"{api_url.removesuffix('/')}/{url.removeprefix('/')}",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8"
        },
        data=json.dumps(body).encode("utf-8")
    )
    if response.status_code != 200:
        error_msg = None
        try:
            error_msg = response.json().get("error", None)
        except:
            pass
        message = f"Error on PUT to Grist route {repr(url)}, got status code {response.status_code}: {repr(error_msg)}"
        print(message)
        print("Response body:")
        print(json.dumps(response.json()))

        raise Exception(message)

    return response.json()

def grist_post(url : str, body : dict | list, query : dict = None) -> dict:
    api_key = get_grist_api_key()

    if query is not None:
        query = urllib.parse.urlencode(query)
        url += "?" + query

    response = requests.post(
        f"{api_url.removesuffix('/')}/{url.removeprefix('/')}",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8"
        },
        data=json.dumps(body).encode("utf-8")
    )

    if response.status_code != 200:
        error_msg = None
        try:
            error_msg = response.json().get("error", None)
        except:
            pass
        message = f"Error on POST to Grist route {repr(url)}, got status code {response.status_code}: {repr(error_msg)}"
        print(message)
        print("Response body:")
        print(json.dumps(response.json()))

        raise Exception(message)
    return response.json()

def grist_delete(url : str, query : dict = None) -> dict:
    api_key = get_grist_api_key()

    if query is not None:
        query = urllib.parse.urlencode(query)
        url += "?" + query

    response = requests.delete(
        f"{api_url.removesuffix('/')}/{url.removeprefix('/')}",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    )

    if response.status_code != 200:
        error_msg = None
        try:
            error_msg = response.json().get("error", None)
        except:
            pass
        message = f"Error on DELETE to Grist route {repr(url)}, got status code {response.status_code}: {repr(error_msg)}"
        print(message)
        print("Response body:")
        print(json.dumps(response.json()))

        raise Exception(message)
    return response.json()

def grist_patch(url : str, body : dict | list, query : dict = None) -> dict:
    api_key = get_grist_api_key()

    if query is not None:
        query = urllib.parse.urlencode(query)
        url += "?" + query

    response = requests.patch(
        f"{api_url.removesuffix('/')}/{url.removeprefix('/')}",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8"
        },
        data=json.dumps(body).encode("utf-8")
    )

    if response.status_code != 200:
        error_msg = None
        try:
            error_msg = response.json().get("error", None)
        except:
            pass
        message = f"Error on PATCH to Grist route {repr(url)}, got status code {response.status_code}: {repr(error_msg)}"
        print(message)
        print("Response body:")
        print(json.dumps(response.json()))

        raise Exception(message)
    return response.json()
