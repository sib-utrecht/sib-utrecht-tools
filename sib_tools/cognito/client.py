import boto3
from time import sleep
import json
import logging
import sys

from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict
from .constants import user_pool_id as user_pool_id
from .auth import get_cognito_credentials
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_cognito_idp import CognitoIdentityProviderClient

# Print account id
# print(boto3.client("sts").get_caller_identity()["Account"])


def create_cognito_client() -> "CognitoIdentityProviderClient":
    a, b, c = get_cognito_credentials()
    return boto3.client(
        "cognito-idp",
        region_name="eu-central-1",
        aws_access_key_id=a,
        aws_secret_access_key=b,
        aws_session_token=c,
    )


cognito_client: "CognitoIdentityProviderClient" = create_cognito_client()
