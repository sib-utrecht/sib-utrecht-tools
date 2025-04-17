import keyring.credentials
import requests
import json
import keyring
from getpass import getpass
import canonical_key
import conscribo_auth
from conscribo_auth import conscribo_post, conscribo_get, conscribo_patch

def get_group_members(group_id) -> set[str]:
    ans = conscribo_get(
        f"/relations/groups/{group_id}/"
    )

    if len(ans["entityGroups"]) != 1:
        print(f"Error: {ans}")
        raise Exception("Unexpected number of entity groups")
    
    ans = ans["entityGroups"][0]
    name = ans["name"]

    print(f"{name} ({ans['id']}) has {len(ans['members'])} members")

    return {
        a["entityId"]
        for a in ans["members"]
    }


def flatten_dict(a : dict) -> dict:
    result = dict()

    for key, value in a.items():
        if isinstance(value, dict):
            for sub_key, sub_value in flatten_dict(value).items():
                result[f"{key}.{sub_key}"] = sub_value
        else:
            result[key] = value
    return result


# ans_canonical = dict()
# for entry in ans.i

def relation_to_canonical(relation):
    canonical = dict()
    
    to_canonical = canonical_key.get_conscribo_to_key()

    flattened_relation = flatten_dict(relation)

    for (key, value) in flattened_relation.items():
        new_key = to_canonical.get(key, None)

        if new_key is not None:
            canonical[new_key] = value
            continue

        other = canonical.setdefault("other", dict())
        other[key] = value

    pronouns = canonical.get("pronouns", None)
    if pronouns is not None and isinstance(pronouns, int):
        pronouns = {
            0: None,
            1: "hij/hem",
            2: "zij/haar",
            4: "die/diens",
            8: "anders:",
        }.get(pronouns, pronouns)
        canonical["pronouns"] = pronouns

    return canonical

def update_relation(canonical):
    canonical = flatten_dict(canonical)
    to_conscribo = canonical_key.get_key_to_conscribo()
    
    conscribo_relation = dict()
    
    for k, v in canonical.items():
        conscribo_key = to_conscribo.get(k, None)

        if conscribo_key is None:
            print(f"Missing translation for {k} to Conscribo field")
            raise Exception(f"Missing translation for {k} to Conscribo field")
        
        conscribo_relation[conscribo_key] = v

    
    print(f"Updating Conscribo relation to\n{json.dumps(conscribo_relation, indent=4)}")

    conscribo_patch(
        f"/relations/{canonical['conscribo_id']}",
        json={
            "fields": conscribo_relation,
        }
    )


    
    print("\n\n")


def list_relations_persoon():
    fieldDefinitions = conscribo_get(
        f"/relations/fieldDefinitions/persoon"
    )["fields"]

    fieldNames = [field["fieldName"] for field in fieldDefinitions]

    # print(f"Field definitions: {fieldDefinitions}")


    result = conscribo_post(
        "/relations/filters/",
        json={
            "requestedFields": fieldNames,
            "filters": [
                # {
                #     "fieldName": "code",
                #     "operator": "=",
                #     "value": [329],  # Vincent
                # }
            ]
        },
    )

    relations = [
        relation_to_canonical(relation)
        for relation in result["relations"].values()
    ]

    return relations
