from laposta_auth import laposta_get, laposta_post, laposta_patch, laposta_delete
import json
import canonical_key
from canonical_key import flatten_dict

# print(json.dumps(laposta_get("/v2/list"), indent=2))

account_id = "tlrp95dlvo"
member_birthday_list_id = "dkrvwo21vt"
member_newsletter_list_id = "s0j3zv9wry"

alumni_birthday_list_id = "luwhwmlq4d"

test_list_id = "szktmg1wta"

def get_list(list_id):
    ans = laposta_get(f"/v2/list/{list_id}")
    return ans["list"]

def get_list_members(list_id):
    ans = laposta_get(f"/v2/member", parameters={
        "list_id": list_id,
    })
    return [
        a["member"] for a in ans["data"]
    ]

def relation_to_canonical(relation):
    canonical = dict()

    to_canonical = canonical_key.get_laposta_to_key()

    flattened_relation = flatten_dict(relation)

    for (key, value) in flattened_relation.items():
        new_key = to_canonical.get(key, None)

        if new_key is not None:
            canonical[new_key] = value
            continue

        other = canonical.setdefault("other", dict())
        other[key] = value

    canonical["laposta_state"] = relation["state"]
    if "date_of_birth" in canonical:
        canonical["date_of_birth"] = canonical["date_of_birth"][:10]

    return canonical

possible_relation_states = [
    "active", "unsubscribed", "unconfirmed", "cleaned"
]


member_newsletter_members = get_list_members(member_newsletter_list_id)

member_birthday_members = get_list_members(member_birthday_list_id)

by_email = dict()

for member in member_birthday_members:
    # if member["email"] != "vincent.kuhlmann@hotmail.com":
        # continue

    member = relation_to_canonical(member)
    email_obj = by_email.setdefault(member["email"], dict())
    email_obj["birthday"] = member

    # active = member["laposta_state"] == "active"
    # print(json.dumps(member, indent=2))

for member in member_newsletter_members:
    # if member["email"] != "vincent.kuhlmann@hotmail.com":
    #     continue

    member = relation_to_canonical(member)
    email_obj = by_email.setdefault(member["email"], dict())
    email_obj["newsletter"] = member

    # active = member["laposta_state"] == "active"
    # print(json.dumps(member, indent=2))

def transform_by_email_entry(entry : dict) -> dict:
    newsletter : dict | None = entry.get("newsletter", None)
    birthday : dict | None = entry.get("birthday", None)

    base = {
        "email": (newsletter or birthday)["email"],
        "send_birthday": False,
        "send_newsletter": False,
    }

    first_names = set()
    last_names = set()

    if newsletter is not None:
        first_names.add(newsletter.get("first_name", None))
        last_names.add(newsletter.get("last_name", None))

        base["send_newsletter"] = True
        base["newsletter_subscription_state"] = newsletter.get("laposta_state", None)

    if birthday is not None:
        base["send_birthday"] = True
        base["date_of_birth"] = birthday.get("date_of_birth", None)
        base["birthday_subscription_state"] = birthday.get("laposta_state", None)

    first_names -= {None}
    last_names -= {None}

    if len(first_names) == 1:
        base["first_name"] = first_names.pop()

    if len(last_names) == 1:
        base["last_name"] = last_names.pop()

    return base

for k, v in by_email.items():
    # print(k)
    # print(json.dumps(v, indent=2))
    print(json.dumps(transform_by_email_entry(v), indent=2))