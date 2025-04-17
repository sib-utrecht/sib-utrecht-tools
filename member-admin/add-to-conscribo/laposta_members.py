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


for member in member_birthday_members:
    if member["email"] != "vincent.kuhlmann@hotmail.com":
        continue

    member = relation_to_canonical(member)


    active = member["laposta_state"] == "active"
    print(json.dumps(member, indent=2))

for member in member_newsletter_members:
    if member["email"] != "vincent.kuhlmann@hotmail.com":
        continue

    member = relation_to_canonical(member)
    active = member["laposta_state"] == "active"
    print(json.dumps(member, indent=2))
