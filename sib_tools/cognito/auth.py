import os
from getpass import getpass
import boto3
import keyring
from dotenv import load_dotenv
import botocore.exceptions

load_dotenv()

# AWS Cognito typical env vars: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN (optional)

cognito_access_key = None
cognito_secret_key = None
cognito_session_token = None

def prompt_credentials():
    access_key = getpass("AWS Access Key ID for Cognito: ")
    secret_key = getpass("AWS Secret Access Key for Cognito: ")
    session_token = getpass("AWS Session Token for Cognito (leave blank if not used): ")
    keyring.set_password("aws-cognito", "access-key-id", access_key)
    keyring.set_password("aws-cognito", "secret-access-key", secret_key)
    if session_token:
        keyring.set_password("aws-cognito", "session-token", session_token)

def clear_if_invalid():
    global cognito_access_key, cognito_secret_key, cognito_session_token

    import boto3
    sts = boto3.client('sts',
        aws_access_key_id=cognito_access_key,
        aws_secret_access_key=cognito_secret_key,
        aws_session_token=cognito_session_token,
        region_name="eu-central-1" 
    )

    try:
        caller_identity = sts.get_caller_identity()
        # If we reach here, the session token is valid
        print(f"Authenticated as {caller_identity['Arn']}")
        print(f"Caller identity: {caller_identity}")

    except (botocore.exceptions.ClientError, botocore.exceptions.NoCredentialsError):
        print(f"AWS Session token is invalid or has expired")
        keyring.delete_password("aws-cognito", "access-key-id")
        keyring.delete_password("aws-cognito", "secret-access-key")
        keyring.delete_password("aws-cognito", "session-token")

        cognito_access_key = None
        cognito_secret_key = None
        cognito_session_token = None


def authenticate():
    global cognito_access_key, cognito_secret_key, cognito_session_token
    # Try environment variables first
    cognito_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    cognito_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    cognito_session_token = os.environ.get("AWS_SESSION_TOKEN")
    if cognito_access_key and cognito_secret_key:
        return cognito_access_key, cognito_secret_key, cognito_session_token
    
    # Fallback to keyring
    cognito_access_key = keyring.get_password("aws-cognito", "access-key-id")
    cognito_secret_key = keyring.get_password("aws-cognito", "secret-access-key")
    cognito_session_token = keyring.get_password("aws-cognito", "session-token")
    if not cognito_session_token:
        cognito_session_token = None

    if cognito_session_token:
        clear_if_invalid()

    if not cognito_access_key or not cognito_secret_key:
        prompt_credentials()
        return authenticate()
    return cognito_access_key, cognito_secret_key, cognito_session_token


def get_cognito_credentials():
    global cognito_access_key, cognito_secret_key, cognito_session_token
    if not cognito_access_key or not cognito_secret_key:
        return authenticate()
    return cognito_access_key, cognito_secret_key, cognito_session_token
