"""
Google Workspace API authentication and group listing utilities.
"""

__all__ = [
    "get_credentials",
    "list_groups_directory_api",
    "list_groups_settings_api",
    "check_available",
    "signout",
]

import os
from typing import Any, List, Dict, cast
from google.oauth2 import service_account
from googleapiclient.discovery import build
import keyring
import getpass
import pathlib
import json

# Manage at https://console.cloud.google.com/
# Manage at https://admin.google.com/ac/owl/domainwidedelegation


# Scopes for Directory API and Groups Settings API
directory_scopes = [
    "https://www.googleapis.com/auth/admin.directory.group.readonly",
    "https://www.googleapis.com/auth/admin.directory.group",
]
groups_settings_scopes = [
    "https://www.googleapis.com/auth/apps.groups.settings",
]


def get_env_or_keyring(key: str, keyring_service: str = "sib_tools_google") -> str | None:
    """
    Get a value from environment or keyring. If not found, return None.
    """
    value = os.environ.get(key)
    if value:
        return value
    value = keyring.get_password(keyring_service, key)
    return value


def prompt_and_store_in_keyring(
    key: str, prompt_text: str, keyring_service: str = "sib_tools_google"
) -> str:
    """
    Prompt the user for a value and store it in keyring.
    """
    value = (
        getpass.getpass(prompt_text)
        if "password" in key.lower()
        else input(prompt_text)
    )
    keyring.set_password(keyring_service, key, value)
    return value


SERVICE_ACCOUNT_FILE = None
ADMIN_EMAIL = None

def prompt_credentials() -> None:
    global SERVICE_ACCOUNT_FILE, ADMIN_EMAIL

    ADMIN_EMAIL = prompt_and_store_in_keyring(
        "GOOGLE_ADMIN_EMAIL", "Enter your Google Workspace admin email: "
    )
    SERVICE_ACCOUNT_FILE = prompt_and_store_in_keyring(
        "GOOGLE_SERVICE_ACCOUNT_FILE",
        "Enter the path to your Google service account JSON file: ",
    )

def ensure_credentials() -> None:
    global SERVICE_ACCOUNT_FILE
    global ADMIN_EMAIL

    SERVICE_ACCOUNT_FILE = SERVICE_ACCOUNT_FILE or get_env_or_keyring(
        "GOOGLE_SERVICE_ACCOUNT_FILE"
    )
    ADMIN_EMAIL = ADMIN_EMAIL or get_env_or_keyring("GOOGLE_ADMIN_EMAIL")

    if not SERVICE_ACCOUNT_FILE or not pathlib.Path(SERVICE_ACCOUNT_FILE).is_file():
        SERVICE_ACCOUNT_FILE = prompt_and_store_in_keyring(
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            "Enter the path to your Google service account JSON file: ",
        )
        if not pathlib.Path(SERVICE_ACCOUNT_FILE).is_file():
            raise FileNotFoundError(
                f"Service account file not found: {SERVICE_ACCOUNT_FILE}"
            )

    if not ADMIN_EMAIL:
        ADMIN_EMAIL = prompt_and_store_in_keyring(
            "GOOGLE_ADMIN_EMAIL", "Enter your Google Workspace admin email: "
        )


def get_credentials(scopes: List[str]) -> Any:
    """
    Returns service account credentials with domain-wide delegation.
    """
    ensure_credentials()
    credentials = service_account.Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
        SERVICE_ACCOUNT_FILE, scopes=scopes
    )
    if ADMIN_EMAIL:
        credentials = credentials.with_subject(ADMIN_EMAIL)
    return credentials


def list_groups_directory_api() -> List[Dict[str, Any]]:
    """
    List Google Groups using the Directory API.
    Returns a list of group resource dicts.
    """
    creds = get_credentials(directory_scopes)
    service = build("admin", "directory_v1", credentials=creds)
    try:
        results = service.groups().list(customer="my_customer").execute()
        return cast(List[Dict[str, Any]], results.get("groups", []))
    except Exception as e:
        print(f"Error listing groups via Directory API: {e}")
        return []


def list_groups_settings_api() -> List[Dict[str, Any]]:
    """
    List Google Groups using the Groups Settings API (requires group emails).
    Returns a list of group settings dicts.
    """
    groups = list_groups_directory_api()
    creds = get_credentials(groups_settings_scopes)
    service = build("groupssettings", "v1", credentials=creds)
    group_settings = []
    for group in groups:
        email = group.get("email")
        if email:
            try:
                settings = service.groups().get(groupUniqueId=email).execute()
                group_settings.append(settings)
            except Exception as e:
                print(f"Error retrieving settings for group {email}: {e}")
    return group_settings


def list_group_members_api(group_email: str) -> list[dict[str, Any]]:
    """
    List members of a Google Group using the Directory API.
    Returns a list of member dicts.
    """
    creds = get_credentials(directory_scopes)
    service = build("admin", "directory_v1", credentials=creds)
    try:
        results = service.members().list(groupKey=group_email).execute()
        return cast(list[dict[str, Any]], results.get("members", []))
    except Exception as e:
        print(f"Error listing members for group {group_email}: {e}")
        return []




def check_available() -> str | None:
    """
    Check if Google admin email is available in keyring.
    """
    return keyring.get_password("sib_tools_google", "GOOGLE_ADMIN_EMAIL")


def show() -> None:
    """Display Google credentials information."""
    service_account_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE") or keyring.get_password("sib_tools_google", "GOOGLE_SERVICE_ACCOUNT_FILE")
    admin_email = os.environ.get("GOOGLE_ADMIN_EMAIL") or keyring.get_password("sib_tools_google", "GOOGLE_ADMIN_EMAIL")
    
    print("\n=== Google Workspace Credentials ===")
    
    if admin_email:
        print(f"Admin Email: {admin_email}")
        print(f"Source: {'Environment Variable' if os.environ.get('GOOGLE_ADMIN_EMAIL') else 'Keyring'}")
    else:
        print("Admin Email: Not set")
    
    if service_account_file:
        print(f"Service Account File: {service_account_file}")
        print(f"Source: {'Environment Variable' if os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE') else 'Keyring'}")
        
        # Try to read service account info
        if pathlib.Path(service_account_file).is_file():
            try:
                with open(service_account_file, 'r') as f:
                    sa_data = json.load(f)
                print(f"Service Account Email: {sa_data.get('client_email', 'Unknown')}")
                print(f"Project ID: {sa_data.get('project_id', 'Unknown')}")
            except Exception as e:
                print(f"Unable to read service account file: {e}")
        else:
            print("Service Account File: File not found at specified path")
    else:
        print("Service Account File: Not set")
    
    print(f"\nScopes:")
    print(f"  Directory API: {', '.join(directory_scopes)}")
    print(f"  Groups Settings API: {', '.join(groups_settings_scopes)}")
    print()


def signout() -> None:
    """
    Sign out of Google by removing admin email from keyring.
    """
    try:
        keyring.delete_password("sib_tools_google", "GOOGLE_ADMIN_EMAIL")
        keyring.delete_password("sib_tools_google", "GOOGLE_SERVICE_ACCOUNT_FILE")
    except keyring.errors.PasswordDeleteError:
        pass
    print("Warning: Not automatically deleting service account json file!!")

