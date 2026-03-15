import os
from dotenv import load_dotenv
load_dotenv()
import requests
import json
import keyring
import keyring.errors
from datetime import datetime, timedelta
from getpass import getpass
from typing import Any, Mapping, cast
from .constants import api_url, username


session_id: str | None = None
session_id_expiration: datetime | None = None

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
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def prompt_credentials() -> None:
    password = getpass(f"Password for {username}: ")
    keyring.set_password("sib-conscribo", "member-admin-bot", password)


"""

Returns the session id of the authenticated user.
"""


def validate_session(session_id: str) -> bool | int:
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

        if not res.ok:
            logger.error(f"Failed to validate session: {res.text}")
            return False

        secsToLogout = res.json().get("secsToLogout")
        return cast("bool | int", secsToLogout)
    
    except Exception as e:
        logger.error(f"Error validating session: {e}")
        return False


def authenticate() -> str:
    global session_id, session_id_expiration
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
    auth_session_data: dict[str, Any] = cast("dict[str, Any]", auth_session) if isinstance(auth_session, dict) else {}

    response_messages_obj = auth_session_data.get("responseMessages")
    if isinstance(response_messages_obj, dict):
        response_messages = cast("dict[str, Any]", response_messages_obj)
        for k, v in response_messages.items():
            if isinstance(v, list):
                messages = list(v)
                for message in messages:
                    logger.info(f"{k}: {json.dumps(message)}")

    status = auth_session_data.get("status")
    if not auth_session_response.ok or status != 200:
        logger.error(
            f"Failed to authenticate, status: {auth_session_response.status_code}|{status}."
        )
        raise Exception("Failed to authenticate")

    auth_session_id = auth_session_data.get("sessionId")
    if not isinstance(auth_session_id, str):
        raise Exception("Failed to authenticate")
    session_id = auth_session_id
    # Cache session id in keyring
    keyring.set_password("sib-conscribo", "session-id", session_id)

    session_id_expiration = datetime.now() + timedelta(minutes=5)
    return session_id


def do_auth() -> None:
    authenticate()
    if session_id is None:
        logger.error("Session id is None after authentication")
        raise Exception("Session id is None after authentication")

    logger.debug(f"Session id length: {len(session_id)}")


def get_conscribo_session_id() -> str:
    global session_id, session_id_expiration

    if (
        session_id is not None and
        session_id_expiration is not None and
        datetime.now() < session_id_expiration
    ):
        return session_id
    # Try to get session id from keyring
    cached_session_id = session_id or keyring.get_password("sib-conscribo", "session-id")
    logger.info(f"Cached session id present: {cached_session_id is not None}")
    if cached_session_id:
        secsToLogout = validate_session(cached_session_id) or 0

        if secsToLogout > 0:
            session_id = cached_session_id
            logger.info("Using cached session id.")
            return session_id
        else:
            logger.info("Cached session id invalid, re-authenticating.")
    # Authenticate and cache new session id
    session_id = authenticate()
    return session_id


def conscribo_get(url: str) -> dict[str, Any]:
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

    return cast("dict[str, Any]", res.json())

def conscribo_delete(url: str, params: None | Mapping[str, Any]) -> dict[str, Any]:
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

    return cast("dict[str, Any]", res.json())

def conscribo_post(url: str, json: dict[str, Any]) -> dict[str, Any]:
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

    return cast("dict[str, Any]", res.json())


def conscribo_patch(url: str, json: dict[str, Any]) -> dict[str, Any]:
    session_id = get_conscribo_session_id()

    return cast("dict[str, Any]", requests.patch(
        f"{api_url}/{url.removeprefix('/')}",
        headers={
            "X-Conscribo-SessionId": session_id,
            "X-Conscribo-API-Version": "1.20240610",
        },
        json=json,
    ).json())


def check_available() -> str | None:
    return keyring.get_password("sib-conscribo", "member-admin-bot")

def show() -> None:
    """Display Conscribo credentials information with redacted password."""
    def redact_password(pwd: str) -> str:
        if not pwd or len(pwd) < 4:
            return "****"
        return pwd[:2] + "*" * (len(pwd) - 2)
    
    password = os.environ.get("CONSCRIBO_PASSWORD") or keyring.get_password("sib-conscribo", "member-admin-bot")
    user = os.environ.get("CONSCRIBO_USERNAME", username)
    
    print("\n=== Conscribo Credentials ===")
    print(f"Username: {user}")
    print(f"API URL: {api_url}")
    
    if password:
        print(f"Password: {redact_password(password)}")
        print(f"Source: {'Environment Variable' if os.environ.get('CONSCRIBO_PASSWORD') else 'Keyring'}")
        
        # Try to validate session
        global session_id
        if session_id:
            validity = validate_session(session_id)
            if validity:
                print(f"Session Status: Active (expires in {validity} seconds)")
            else:
                print("Session Status: Invalid or expired")
        else:
            print("Session Status: Not authenticated yet")
    else:
        print("Password: Not set")
    print()

def signout() -> None:
    try:
        keyring.delete_password("sib-conscribo", "member-admin-bot")
    except keyring.errors.PasswordDeleteError:
        pass
