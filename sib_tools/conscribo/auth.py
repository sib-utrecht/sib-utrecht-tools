import keyring.credentials
import requests
import json
import keyring
from getpass import getpass

from traitlets import Any
from .constants import api_url, username

session_id = None

# Define ApiRequestError for better error handling
class ApiRequestError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def prompt_credentials():
    password = getpass(f"Password for {username}: ")

    # keyring.set_password('sib-conscribo', "script1-username", username)
    # keyring.set_password('sib-conscribo', "script1-password", password)
    keyring.set_password("sib-conscribo", "member-admin-bot", password)


"""

Returns the session id of the authenticated user.
"""


def authenticate() -> str:
    global session_id

    # username = keyring.get_password('sib-conscribo', "script1-username")
    # password = keyring.get_password('sib-conscribo', "script1-password")
    password = keyring.get_password("sib-conscribo", "member-admin-bot")

    if username is None or password is None:
        prompt_credentials()
        return authenticate()

    print(f"Password length: {len(password)}")

    auth_session_response = requests.post(
        f"{api_url}/sessions/",
        headers={
            "X-Conscribo-API-Version": "1.20240610",
        },
        json={
            "userName": username,
            "passPhrase": password,
        },
    )

    print(f"Auth session ok: {auth_session_response.ok}")

    auth_session = auth_session_response.json()

    for k, v in (auth_session.get("responseMessages") or dict()).items():
        for message in v:
            print(f"{k}: {json.dumps(message)}")

    if not auth_session_response.ok or auth_session["status"] != 200:
        print(
            f"Failed to authenticate, status: {auth_session_response.status_code}|{auth_session['status']}."
        )
        raise Exception("Failed to authenticate")

    user_display_name = auth_session["userDisplayName"]
    session_id = auth_session["sessionId"]

    return session_id


def do_auth():
    authenticate()

    print(f"Session id length: {len(session_id)}")


def get_conscribo_session_id():
    global session_id

    if session_id is None:
        session_id = authenticate()

    return session_id


def conscribo_get(url: str) -> dict:
    session_id = get_conscribo_session_id()

    res = requests.get(
        f"{api_url}/{url.removeprefix('/')}",
        headers={
            "X-Conscribo-SessionId": session_id,
            "X-Conscribo-API-Version": "1.20240610",
        },
    )

    if not res.ok:
        raise ApiRequestError(f"Failed to get {url}: {res.text}", status_code=res.status_code)

    return res.json()

def conscribo_delete(url: str, params : None | dict[str, Any]) -> dict:
    session_id = get_conscribo_session_id()

    res = requests.delete(
        f"{api_url}/{url.removeprefix('/')}",
        headers={
            "X-Conscribo-SessionId": session_id,
            "X-Conscribo-API-Version": "1.20240610",
        },
        params=params,
    )

    if not res.ok:
        raise ApiRequestError(f"Failed to delete {url}: {res.text}", status_code=res.status_code)

    return res.json()

def conscribo_post(url : str, json : dict) -> dict:
    session_id = get_conscribo_session_id()

    res = requests.post(
        f"{api_url}/{url.removeprefix('/')}",
        headers={
            "X-Conscribo-SessionId": session_id,
            "X-Conscribo-API-Version": "1.20240610",
        },
        json=json,
    )
    
    if not res.ok:
        raise ApiRequestError(f"Failed to post to {url}: {res.text}", status_code=res.status_code)
    
    return res.json()


def conscribo_patch(url : str, json : dict) -> dict:
    session_id = get_conscribo_session_id()

    return requests.patch(
        f"{api_url}/{url.removeprefix('/')}",
        headers={
            "X-Conscribo-SessionId": session_id,
            "X-Conscribo-API-Version": "1.20240610",
        },
        json=json,
    ).json()
