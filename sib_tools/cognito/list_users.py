import boto3
from time import sleep
import json
import logging
import sys

from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict
from .constants import user_pool_id
from .auth import get_cognito_credentials
from typing import Any
from .client import cognito_client

cognito_to_canonical_dict = canonical_key.get_cognito_to_key()

def cognito_user_meta_to_canonical(user):
    to_canonical = cognito_to_canonical_dict

    flattened_user = flatten_dict(user)
    canonical = dict()
    for key, value in flattened_user.items():
        new_key = to_canonical.get(key, None)

        if new_key is not None:
            canonical[new_key] = value
            continue

        other = canonical.setdefault("other", dict())
        other[key] = value

    return canonical


def cognito_user_to_canonical(user : dict[str, Any]) -> dict[str, Any]:
    username = user.get("Username")
    usercreatedate = user.get("UserCreateDate")
    userlastmodifieddate = user.get("UserLastModifiedDate")
    user_status = user.get("UserStatus")
    user_enabled = user.get("Enabled")

    attributes = user.pop("Attributes", [])
    attributes_dict = {attr["Name"]: attr["Value"] for attr in attributes}
    canonical = cognito_user_meta_to_canonical(attributes_dict)

    if "wp_user_id" in canonical:
        canonical["wp_user_id"] = int(canonical["wp_user_id"])

    user["UserCreateDate"] = str(usercreatedate)
    user["UserLastModifiedDate"] = str(userlastmodifieddate)

    cleaned_user = {"meta": user, **canonical}

    return cleaned_user


def canonical_to_cognito_user(user):
    to_cognito = canonical_key.get_key_to_cognito()

    flattened_user = flatten_dict(user)
    attributes = []
    for key, value in flattened_user.items():
        new_key = to_cognito.get(key, None)

        if key == "email_verified":
            new_key = new_key or "email_verified"

        if new_key is None:
            # logging.warning(f"[canonical_to_cognito_user] Key {key} not found in Cognito mapping, skipping.")
            continue

        attributes.append({"Name": new_key, "Value": value})

        # other = user.setdefault("other", dict())
        # other[key] = value

    return {
        "Username": user.get("cognito_sub") or user.get("email"),
        "Attributes": attributes,
    }


def list_cognito_users_canonical():
    cognito_users = list_all_cognito_users()
    return [cognito_user_to_canonical(user) for user in cognito_users]


def list_all_cognito_users():
    cognito_users = []

    response = cognito_client.list_users(
        UserPoolId=user_pool_id,
        Limit=10,
    )

    while True:
        cognito_users.extend(response["Users"])

        paginationToken = response.get("PaginationToken")
        if paginationToken is None:
            break

        response = cognito_client.list_users(
            UserPoolId=user_pool_id,
            PaginationToken=paginationToken,
        )
        sleep(0.1)

    return cognito_users
