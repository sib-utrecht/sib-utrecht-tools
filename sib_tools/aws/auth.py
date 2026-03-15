import os
from getpass import getpass
import boto3
import keyring
from dotenv import load_dotenv
import botocore.exceptions
from importlib import import_module
from typing import Any, Literal, Protocol, cast

class PasswordDeleteError(Exception):
    pass

# Optional dependency: avoid static import so missing stubs/packages don't fail type checking.
try:
    _cryptfile_module = import_module("keyrings.cryptfile.cryptfile")
    _cryptfile_keyring_cls = getattr(_cryptfile_module, "CryptFileKeyring", None)
except Exception:
    _cryptfile_keyring_cls = None


class STSClientProtocol(Protocol):
    def get_caller_identity(self) -> dict[str, Any]: ...


class SESClientProtocol(Protocol):
    def send_raw_email(
        self,
        *,
        Source: str,
        Destinations: list[str],
        RawMessage: dict[str, bytes],
    ) -> dict[str, Any]: ...


class S3ClientProtocol(Protocol):
    pass


class IAMClientProtocol(Protocol):
    def get_user(self) -> dict[str, Any]: ...
    def list_access_keys(self, *, UserName: str) -> dict[str, Any]: ...
    def create_access_key(self, *, UserName: str) -> dict[str, Any]: ...
    def delete_access_key(self, *, UserName: str, AccessKeyId: str) -> dict[str, Any]: ...

load_dotenv()

# AWS Cognito typical env vars: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN (optional)

# Can be one of: "env" | "keyring" | "cleared" | None
aws_credentials_origin = None
aws_access_key = None
aws_secret_key = None
aws_session_token = None
allow_from_env = True

def _client(service_name: Literal["sts", "ses", "s3", "iam"], **kwargs: Any) -> Any:
    client_factory = getattr(boto3, "client")
    return client_factory(cast(str, service_name), **kwargs)


def prompt_credentials() -> None:
    global aws_access_key, aws_secret_key, aws_session_token
    global aws_credentials_origin
    global allow_from_env

    existing_access_key = keyring.get_password("aws-cognito", "access-key-id")
    if existing_access_key:
        print(f"Existing AWS Access Key ID found in keyring: {existing_access_key}")
        print("Do you want to use the existing credentials? (y/N)")
        if input().strip().lower() == 'y':
            allow_from_env = False
            aws_credentials_origin = None
            fetch_credentials()
            return

    access_key = getpass("AWS Access Key ID for Cognito: ")
    secret_key = getpass("AWS Secret Access Key for Cognito: ")
    session_token = getpass("AWS Session Token for Cognito (leave blank if not used): ")
    keyring.set_password("aws-cognito", "access-key-id", access_key)
    keyring.set_password("aws-cognito", "secret-access-key", secret_key)
    keyring.set_password("aws-cognito", "session-token", session_token)

    aws_access_key = access_key
    aws_secret_key = secret_key
    aws_session_token = session_token if session_token else None
    aws_credentials_origin = "keyring"


def fetch_credentials() -> tuple[str | None, str | None, str | None]:
    global aws_access_key, aws_secret_key, aws_session_token, aws_credentials_origin
    if aws_credentials_origin == "cleared":
        aws_access_key = None
        aws_secret_key = None
        aws_session_token = None
        return None, None, None

    if allow_from_env:
        # Try environment variables first
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        aws_session_token = os.environ.get("AWS_SESSION_TOKEN")
        if aws_access_key and aws_secret_key:
            aws_credentials_origin = "env"
            return aws_access_key, aws_secret_key, aws_session_token
    
    # Fallback to keyring
    aws_access_key = keyring.get_password("aws-cognito", "access-key-id")
    aws_secret_key = keyring.get_password("aws-cognito", "secret-access-key")
    aws_session_token = keyring.get_password("aws-cognito", "session-token")
    if not aws_session_token:
        # If empty, use None instead
        aws_session_token = None

    if aws_secret_key:
        aws_credentials_origin = "keyring"
    else:
        aws_credentials_origin = None
    
    return aws_access_key, aws_secret_key, aws_session_token


def clear_if_invalid() -> None:
    global aws_access_key, aws_secret_key, aws_session_token, aws_credentials_origin
    fetch_credentials()

    if not aws_access_key:
        return

    sts = cast(
        STSClientProtocol,
        _client(
        'sts',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        aws_session_token=aws_session_token,
        region_name="eu-central-1" 
        )
    )

    try:
        caller_identity = sts.get_caller_identity()
        # If we reach here, the session token is valid
        print(f"Authenticated as {caller_identity['Arn']}")
        print(f"Caller identity: {caller_identity}")

    except (botocore.exceptions.ClientError, botocore.exceptions.NoCredentialsError):
        print(f"AWS Session token is invalid or has expired")
        if aws_credentials_origin == "keyring":
            for k in ["access-key-id", "secret-access-key", "session-token"]:
                try:
                    keyring.delete_password("aws-cognito", k)
                    print(f"Deleted AWS Cognito {k} from keyring")
                except PasswordDeleteError:
                    pass

        aws_access_key = None
        aws_secret_key = None
        aws_session_token = None
        aws_credentials_origin = "cleared"


def ensure_credentials() -> None:
    fetch_credentials()
    
    if aws_session_token:
        clear_if_invalid()

    if not aws_access_key or not aws_secret_key:
        prompt_credentials()

def get_aws_credentials() -> tuple[str | None, str | None, str | None]:
    if not aws_access_key or not aws_secret_key:
        ensure_credentials()
    return aws_access_key, aws_secret_key, aws_session_token

def get_ses_client() -> SESClientProtocol:
    access_key, secret_key, session_token = get_aws_credentials()
    return cast(
        SESClientProtocol,
        _client(
            'ses',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name="eu-central-1"
        ),
    )

def get_s3_client() -> S3ClientProtocol:
    access_key, secret_key, session_token = get_aws_credentials()
    return cast(
        S3ClientProtocol,
        _client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name="eu-central-1"
        ),
    )

def get_iam_client() -> IAMClientProtocol:
    access_key, secret_key, session_token = get_aws_credentials()
    return cast(
        IAMClientProtocol,
        _client(
            'iam',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
        ),
    )

def rotate_aws_credentials() -> None:
    """
    Rotates the AWS access key for the current IAM user, stores the new key in keyring,
    and optionally deletes the old key. Requires current credentials to be valid and have
    iam:CreateAccessKey, iam:DeleteAccessKey, and iam:ListAccessKeys permissions for self.
    """
    print("Checking validity of current credentials...")
    clear_if_invalid()
    if not aws_access_key or not aws_secret_key:
        print("Current credentials are invalid or not set. Please authenticate first.")
        return

    print("Rotating AWS credentials for the current IAM user...")
    iam = get_iam_client()
    user = str(iam.get_user()["User"]["UserName"])
    print(f"Current IAM user: {user}")

    # List current access keys
    keys = cast(list[dict[str, str]], iam.list_access_keys(UserName=user)["AccessKeyMetadata"])
    if len(keys) >= 2:
        print("You already have 2 access keys. Please delete one before rotating.")
        return
    old_key = keys[0]["AccessKeyId"] if keys else None

    # Create new access key
    new_key = cast(dict[str, str], iam.create_access_key(UserName=user)["AccessKey"])
    print(f"New access key created: {new_key['AccessKeyId']}")

    # Store new credentials in keyring
    keyring.set_password("aws-cognito", "access-key-id", new_key["AccessKeyId"])
    keyring.set_password("aws-cognito", "secret-access-key", new_key["SecretAccessKey"])
    print("New credentials stored in keyring.")

    # Optionally delete old key
    if old_key:
        iam.delete_access_key(UserName=user, AccessKeyId=old_key)

    print("Rotation complete.")

def check_available() -> bool:
    return len(keyring.get_password("aws-cognito", "access-key-id") or "") > 0

def show() -> None:
    """Display AWS credentials information with redacted keys."""
    def redact_key(key: str | None) -> str:
        return "****"
        # if not key or len(key) < 8:
        #     return "****"
        # return key[:4] + "*" * (len(key) - 8) + key[-4:]
    
    access_key = os.environ.get("AWS_ACCESS_KEY_ID") or keyring.get_password("aws-cognito", "access-key-id")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY") or keyring.get_password("aws-cognito", "secret-access-key")
    session_token = os.environ.get("AWS_SESSION_TOKEN") or keyring.get_password("aws-cognito", "session-token")
    
    print("\n=== AWS (Cognito & Email) Credentials ===")
    if access_key:
        print(f"Access Key ID: {access_key}")
        print(f"Source: {'Environment Variable' if os.environ.get('AWS_ACCESS_KEY_ID') else 'Keyring'}")
    else:
        print("Access Key ID: Not set")
    
    if secret_key:
        print(f"Secret Access Key: {redact_key(secret_key)}")
    else:
        print("Secret Access Key: Not set")
    
    if session_token:
        print(f"Session Token: {redact_key(session_token)}")
    else:
        print("Session Token: Not set")
    
    # Try to get caller identity if credentials are available
    if access_key and secret_key:
        try:
            sts = cast(
                STSClientProtocol,
                _client(
                'sts',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=session_token,
                region_name="eu-central-1"
                ),
            )
            caller_identity = sts.get_caller_identity()
            print(f"IAM User ARN: {caller_identity.get('Arn', 'Unknown')}")
            print(f"Account ID: {caller_identity.get('Account', 'Unknown')}")
            print(f"User ID: {caller_identity.get('UserId', 'Unknown')}")
        except Exception as e:
            print(f"Unable to verify credentials: {e}")
    print()

def signout() -> None:
    for k in ["access-key-id", "secret-access-key", "session-token"]:
        try:
            keyring.delete_password("aws-cognito", k)
        except PasswordDeleteError:
            pass
