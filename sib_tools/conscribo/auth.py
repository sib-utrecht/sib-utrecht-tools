import os
from dotenv import load_dotenv
load_dotenv()
import keyring.credentials
import requests
import json
import keyring
from getpass import getpass

from traitlets import Any
from .constants import api_url, username

session_id = None

# Add logging for Conscribo
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.FileHandler("conscribo_api.log")
handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
logger.addHandler(handler)

# Also print to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(console_handler)

# Define ApiRequestError for better error handling
class ApiRequestError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def prompt_credentials():
    password = getpass(f"Password for {username}: ")
    keyring.set_password("sib-conscribo", "member-admin-bot", password)


"""

Returns the session id of the authenticated user.
"""


def validate_session(session_id: str) -> bool:
    """
    Checks if the session is still valid by calling /sessions/.
    Returns True if valid, False otherwise.
    """
    try:
        res = requests.get(
            f"{api_url}/sessions/",
            headers={
                "X-Conscribo-SessionId": session_id,
                "X-Conscribo-API-Version": "1.20240610",
            },
        )
        if res.status_code == 400:
            logger.info("Session invalid (400), need to re-authenticate.")
            return False
        return res.ok
    except Exception as e:
        logger.error(f"Error validating session: {e}")
        return False


def authenticate() -> str:
    global session_id
    # Try environment variable first
    password = os.environ.get("CONSCRIBO_PASSWORD")
    user = os.environ.get("CONSCRIBO_USERNAME", username)
    if password:
        logger.debug("Using password from CONSCRIBO_PASSWORD env var.")
    else:
        password = keyring.get_password("sib-conscribo", "member-admin-bot")
        if password is None:
            prompt_credentials()
            return authenticate()

    logger.debug(f"Password length: {len(password)}")

    auth_session_response = requests.post(
        f"{api_url}/sessions/",
        headers={
            "X-Conscribo-API-Version": "1.20240610",
        },
        json={
            "userName": user,
            "passPhrase": password,
        },
    )

    logger.debug(f"Auth session ok: {auth_session_response.ok}")

    auth_session = auth_session_response.json()

    for k, v in (auth_session.get("responseMessages") or dict()).items():
        for message in v:
            logger.info(f"{k}: {json.dumps(message)}")

    if not auth_session_response.ok or auth_session["status"] != 200:
        logger.error(
            f"Failed to authenticate, status: {auth_session_response.status_code}|{auth_session['status']}."
        )
        raise Exception("Failed to authenticate")

    user_display_name = auth_session["userDisplayName"]
    session_id = auth_session["sessionId"]
    # Cache session id in keyring
    keyring.set_password("sib-conscribo", "session-id", session_id)
    return session_id


def do_auth():
    authenticate()
    logger.debug(f"Session id length: {len(session_id)}")


def get_conscribo_session_id():
    global session_id
    if session_id is not None:
        return session_id
    # Try to get session id from keyring
    cached_session_id = keyring.get_password("sib-conscribo", "session-id")
    logger.info(f"Cached session id present: {cached_session_id is not None}")
    if cached_session_id:
        if validate_session(cached_session_id):
            session_id = cached_session_id
            logger.info("Using cached session id.")
            return session_id
        else:
            logger.info("Cached session id invalid, re-authenticating.")
    # Authenticate and cache new session id
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


def check_available():
    return keyring.get_password("sib-conscribo", "member-admin-bot")

def signout():
    try:
        keyring.delete_password("sib-conscribo", "member-admin-bot")
    except keyring.errors.PasswordDeleteError:
        pass
