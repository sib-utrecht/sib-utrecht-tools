import keyring.credentials
import requests
import json
import keyring
from getpass import getpass
import canonical_key

api_url = "https://api.secure.conscribo.nl/sib-utrecht"

session_id = None

username = "member-admin-bot"

def prompt_credentials():
    password = getpass(f"Password for {username}: ")

    # keyring.set_password('sib-conscribo', "script1-username", username)
    # keyring.set_password('sib-conscribo', "script1-password", password)
    keyring.set_password('sib-conscribo', "member-admin-bot", password)


"""

Returns the session id of the authenticated user.
"""
def authenticate() -> str:
    global session_id

    # username = keyring.get_password('sib-conscribo', "script1-username")
    # password = keyring.get_password('sib-conscribo', "script1-password")
    password = keyring.get_password('sib-conscribo', "member-admin-bot")

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
        }
    )

    print(f"Auth session ok: {auth_session_response.ok}")

    auth_session = auth_session_response.json()

    for (k, v) in (auth_session.get("responseMessages") or dict()).items():
        for message in v:
            print(f"{k}: {json.dumps(message)}")


    if not auth_session_response.ok or auth_session["status"] != 200:
        print(f"Failed to authenticate, status: {auth_session_response.status_code}|{auth_session['status']}.")
        raise Exception("Failed to authenticate")
        
    user_display_name = auth_session["userDisplayName"]
    session_id = auth_session["sessionId"]

    return session_id

authenticate()

print(f"Session id length: {len(session_id)}")

fieldDefinitions = requests.get(
    f"{api_url}/relations/fieldDefinitions/persoon",
    headers={
        "X-Conscribo-SessionId": session_id,
        "X-Conscribo-API-Version": "1.20240610",
    },
).json()["fields"]

fieldNames = [field["fieldName"] for field in fieldDefinitions]



result = requests.post(
    f"{api_url}/relations/filters/",
    headers={
        "X-Conscribo-SessionId": session_id,
        "X-Conscribo-API-Version": "1.20240610",
    },
    json={
        "requestedFields": fieldNames,
        "filters": [
            {
                "fieldName": "code",
                "operator": "=",
                "value": [329],  # Vincent
            }
        ]
    },
)

print(result)
print(result.ok)

ans = result.json()
print(json.dumps(ans, indent=2))

# ans_canonical = dict()
# for entry in ans.i

to_canonical = canonical_key.get_conscribo_to_key()

relations_dict : dict = ans["relations"]
relations : list[dict] = relations_dict.values()

for relation in relations:
    canonical = dict()

    for (key, value) in relation.items():
        new_key = to_canonical.get(key, None)

        if new_key is not None:
            canonical[new_key] = value
            continue

        other = canonical.setdefault("other", dict())
        other[key] = value
        
    print("\n")
    print(json.dumps(canonical, indent=2))
    print("\n\n")
