import os
from getpass import getpass
import boto3
import boto3.session
import keyring
from dotenv import load_dotenv
import botocore.exceptions
import keyring
from keyrings.cryptfile.cryptfile import CryptFileKeyring

load_dotenv()

# AWS Cognito typical env vars: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN (optional)

# Can be one of: "env" | "keyring" | "cleared" | None
aws_credentials_origin = None
aws_access_key = None
aws_secret_key = None
aws_session_token = None
allow_from_env = True

def prompt_credentials():
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


def fetch_credentials():
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


def clear_if_invalid():
    global aws_access_key, aws_secret_key, aws_session_token
    fetch_credentials()

    if not aws_access_key:
        return

    sts = boto3.client('sts',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        aws_session_token=aws_session_token,
        region_name="eu-central-1" 
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
                except keyring.errors.PasswordDeleteError:
                    pass

        aws_access_key = None
        aws_secret_key = None
        aws_session_token = None
        aws_credentials_origin = "cleared"


def ensure_credentials():
    fetch_credentials()
    
    if aws_session_token:
        clear_if_invalid()

    if not aws_access_key or not aws_secret_key:
        prompt_credentials()

def get_aws_credentials():
    if not aws_access_key or not aws_secret_key:
        ensure_credentials()
    return aws_access_key, aws_secret_key, aws_session_token

def get_ses_client():
    access_key, secret_key, session_token = get_aws_credentials()
    return boto3.client(
        'ses',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token,
        region_name="eu-central-1"
    )

def get_s3_client():
    access_key, secret_key, session_token = get_aws_credentials()
    return boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token,
        region_name="eu-central-1"
    )

def get_iam_client():
    access_key, secret_key, session_token = get_aws_credentials()
    return boto3.client(
        'iam',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token,
    )

def rotate_aws_credentials():
    """
    Rotates the AWS access key for the current IAM user, stores the new key in keyring,
    and optionally deletes the old key. Requires current credentials to be valid and have
    iam:CreateAccessKey, iam:DeleteAccessKey, and iam:ListAccessKeys permissions for self.
    """
    import boto3
    import keyring
    import getpass

    print("Checking validity of current credentials...")
    clear_if_invalid()
    if not aws_access_key or not aws_secret_key:
        print("Current credentials are invalid or not set. Please authenticate first.")
        return

    print("Rotating AWS credentials for the current IAM user...")
    iam = get_iam_client()
    user = iam.get_user()["User"]["UserName"]
    print(f"Current IAM user: {user}")

    # List current access keys
    keys = iam.list_access_keys(UserName=user)["AccessKeyMetadata"]
    if len(keys) >= 2:
        print("You already have 2 access keys. Please delete one before rotating.")
        return
    old_key = keys[0]["AccessKeyId"] if keys else None

    # Create new access key
    new_key = iam.create_access_key(UserName=user)["AccessKey"]
    print(f"New access key created: {new_key['AccessKeyId']}")

    # Store new credentials in keyring
    keyring.set_password("aws-cognito", "access-key-id", new_key["AccessKeyId"])
    keyring.set_password("aws-cognito", "secret-access-key", new_key["SecretAccessKey"])
    print("New credentials stored in keyring.")

    # Optionally delete old key
    if old_key:
        iam.delete_access_key(UserName=user, AccessKeyId=old_key)

    print("Rotation complete.")

def check_available():
    return len(keyring.get_password("aws-cognito", "access-key-id") or "") > 0

def signout():
    for k in ["access-key-id", "secret-access-key", "session-token"]:
        try:
            keyring.delete_password("aws-cognito", k)
        except keyring.errors.PasswordDeleteError:
            pass
