import json
import logging
from argparse import ArgumentParser, Namespace

from .cognito.client import cognito_client
from .cognito.constants import user_pool_id


def _attributes_to_dict(attrs: list[dict]) -> dict:
    return {a.get("Name"): a.get("Value") for a in (attrs or [])}


def _find_user_by_email(email: str):
    # Cognito filter syntax requires quoted value
    resp = cognito_client.list_users(UserPoolId=user_pool_id, Filter=f'email = "{email}"')
    users = resp.get("Users", [])
    if not users:
        return None
    if len(users) > 1:
        # Prefer exact match on attribute value
        for u in users:
            attrs = _attributes_to_dict(u.get("Attributes", []))
            if attrs.get("email") == email:
                return u
        return users[0]
    return users[0]


def _list_webauthn_credentials_with_token(access_token: str) -> list:
    creds_all = []
    next_token = None
    while True:
        params = {"AccessToken": access_token}
        if next_token:
            params["NextToken"] = next_token
        resp = cognito_client.list_webauthn_credentials(**params)
        creds = resp.get("WebAuthnCredentials") or resp.get("Credentials") or []
        creds_all.extend(creds)
        next_token = resp.get("NextToken") or resp.get("PaginationToken")
        if not next_token:
            break
    return creds_all


def _get_user_auth_factors_with_token(access_token: str) -> dict:
    return cognito_client.get_user_auth_factors(AccessToken=access_token)


def handle_auth_show(args: Namespace):
    email = args.email
    user = _find_user_by_email(email)
    if not user:
        print(f"No Cognito user found for email: {email}")
        return

    attrs = _attributes_to_dict(user.get("Attributes", []))
    out = {
        "Username": user.get("Username"),
        "Enabled": user.get("Enabled"),
        "UserStatus": user.get("UserStatus"),
        "UserCreateDate": str(user.get("UserCreateDate")),
        "UserLastModifiedDate": str(user.get("UserLastModifiedDate")),
        "email": attrs.get("email"),
        "email_verified": attrs.get("email_verified"),
        "sub": attrs.get("sub"),
        "custom:wp-userid": attrs.get("custom:wp-userid"),
        "custom:entity-id": attrs.get("custom:entity-id"),
        "attributes": attrs,
    }

    access_token = getattr(args, "access_token", None)

    # Include WebAuthn credentials (requires AccessToken)
    if access_token:
        try:
            out["webauthn_credentials"] = _list_webauthn_credentials_with_token(access_token)
        except Exception as e:
            out["webauthn_credentials_error"] = str(e)
    else:
        out["webauthn_credentials_note"] = "Pass --access-token to include WebAuthn credentials"

    # Include auth factors (requires AccessToken)
    if access_token:
        try:
            out["auth_factors"] = _get_user_auth_factors_with_token(access_token)
        except Exception as e:
            out["auth_factors_error"] = str(e)
    else:
        out["auth_factors_note"] = "Pass --access-token to include user auth factors"

    print(json.dumps(out, indent=2))


def handle_auth_remove_password(args: Namespace):
    email = args.email
    user = _find_user_by_email(email)
    if not user:
        print(f"No Cognito user found for email: {email}")
        return
    username = user.get("Username")
    try:
        cognito_client.admin_reset_user_password(UserPoolId=user_pool_id, Username=username)
        print(f"Password reset initiated for {email} (Username={username}).")
    except Exception as e:
        print(f"Failed to reset/remove password for {email}: {e}")


def handle_auth_remove_passkeys(args: Namespace):
    email = args.email
    user = _find_user_by_email(email)
    if not user:
        print(f"No Cognito user found for email: {email}")
        return

    access_token = getattr(args, "access_token", None)
    if not access_token:
        print("--access-token is required to remove passkeys (user-level API)")
        return

    total = 0
    try:
        creds = _list_webauthn_credentials_with_token(access_token)
        if not creds:
            print(f"No passkeys found for {email}.")
            return
        for c in creds:
            cred_id = c.get("CredentialId") or c.get("CredentialID") or c.get("Id")
            display_name = c.get("Name") or c.get("FriendlyName") or "(no name)"
            if not cred_id:
                continue
            try:
                cognito_client.delete_webauthn_credential(
                    AccessToken=access_token,
                    CredentialId=cred_id,
                )
                total += 1
                print(f"Deleted passkey '{display_name}' ({cred_id}) for {email}.")
            except Exception as e:
                print(f"Failed to delete passkey {cred_id} for {email}: {e}")
        print(f"Removed {total} passkey(s) for {email}.")
    except Exception as e:
        print(f"Failed to list/remove passkeys for {email}: {e}")


def _set_email_verified(email: str, verified: bool):
    user = _find_user_by_email(email)
    if not user:
        print(f"No Cognito user found for email: {email}")
        return
    username = user.get("Username")
    try:
        cognito_client.admin_update_user_attributes(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[{"Name": "email_verified", "Value": "true" if verified else "false"}],
        )
        print(
            f"Set email_verified={verified} for {email} (Username={username})."
        )
    except Exception as e:
        print(f"Failed to update email_verified for {email}: {e}")


def handle_auth_mark_email_verified(args: Namespace):
    _set_email_verified(args.email, True)


def handle_auth_mark_email_unverified(args: Namespace):
    _set_email_verified(args.email, False)


def handle_auth_set_mfa_preference(args: Namespace):
    """Set a user's MFA preference using AdminSetUserMFAPreference.

    Supports 'email' (EmailMfaSettings) and 'totp' (SoftwareTokenMfaSettings / TOTP).
    """
    email = args.email
    method = args.method
    state = args.state

    user = _find_user_by_email(email)
    if not user:
        print(f"No Cognito user found for email: {email}")
        return

    username = user.get("Username")

    # Map state to Enabled/PreferredMfa
    enabled = False
    preferred = False
    if state == "enable":
        enabled = True
    if state == "preferred":
        enabled = True
        preferred = True

    try:
        params = {
            "UserPoolId": user_pool_id,
            "Username": username,
        }
        if method == "email":
            params["EmailMfaSettings"] = {
                "Enabled": enabled,
                "PreferredMfa": preferred,
            }
        elif method == "totp":
            # Map 'totp' to TOTP Software Token MFA settings
            params["SoftwareTokenMfaSettings"] = {
                "Enabled": enabled,
                "PreferredMfa": preferred,
            }
        cognito_client.admin_set_user_mfa_preference(**params)
        print(f"Set {method} MFA to '{state}' for {email} (Username={username}).")
    except Exception as e:
        print(f"Failed to set {method} MFA '{state}' for {email}: {e}")


def add_parse_args(parser: ArgumentParser):
    parser.set_defaults(func=lambda args: parser.print_help())
    sub = parser.add_subparsers(dest="auth_cmd", title="Auth actions")

    p_show = sub.add_parser("show", help="Show Cognito user info by email")
    p_show.add_argument("email", type=str, help="Email of the user")
    p_show.add_argument("--access-token", dest="access_token", type=str, help="User AccessToken to include WebAuthn credentials and auth factors")
    p_show.set_defaults(func=handle_auth_show)

    p_rmpw = sub.add_parser("remove_password", help="Reset/remove password for user (forces reset)")
    p_rmpw.add_argument("email", type=str, help="Email of the user")
    p_rmpw.set_defaults(func=handle_auth_remove_password)

    p_rmkeys = sub.add_parser("remove_passkeys", help="Remove all passkeys registered for the user")
    p_rmkeys.add_argument("email", type=str, help="Email of the user")
    p_rmkeys.add_argument("--access-token", dest="access_token", type=str, required=False, help="User AccessToken required to list and delete passkeys")
    p_rmkeys.set_defaults(func=handle_auth_remove_passkeys)

    p_v = sub.add_parser("mark_email_verified", help="Mark user's email as verified")
    p_v.add_argument("email", type=str, help="Email of the user")
    p_v.set_defaults(func=handle_auth_mark_email_verified)

    p_uv = sub.add_parser("mark_email_unverified", help="Mark user's email as unverified")
    p_uv.add_argument("email", type=str, help="Email of the user")
    p_uv.set_defaults(func=handle_auth_mark_email_unverified)

    p_set = sub.add_parser(
        "set_mfa_preference",
        help=(
            "Set user's MFA preference using AdminSetUserMFAPreference. "
            "Methods: 'email' (EmailMfaSettings) or 'totp' (SoftwareTokenMfaSettings/TOTP)."
        ),
    )
    p_set.add_argument("email", type=str, help="Email of the user")
    p_set.add_argument("method", choices=["email", "totp"], help="MFA method to configure")
    p_set.add_argument("state", choices=["disable", "enable", "preferred"], help="Desired state")
    p_set.set_defaults(func=handle_auth_set_mfa_preference)

    return parser
