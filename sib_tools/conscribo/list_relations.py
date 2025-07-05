import keyring.credentials
import requests
import json
import keyring
from getpass import getpass
from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict

from .constants import api_url
from .auth import conscribo_post, conscribo_get, conscribo_patch

group_wil_geen_email_van_ons_ontvangen = 36

ans = conscribo_get(f"/relations/groups/")
entity_groups = ans["entityGroups"]


def get_group_members_cached(group_id) -> set[str]:
    group = next((g for g in entity_groups if g["id"] == str(group_id)), None)
    if group is None:
        return get_group_members(group_id)

    return {a["entityId"] for a in group["members"]}


def get_group_members(group_id) -> set[str]:
    ans = conscribo_get(f"/relations/groups/{group_id}/")

    if len(ans["entityGroups"]) != 1:
        print(f"Error: {ans}")
        raise Exception("Unexpected number of entity groups")

    ans = ans["entityGroups"][0]
    name = ans["name"]

    print(f"{name} ({ans['id']}) has {len(ans['members'])} members")

    return {a["entityId"] for a in ans["members"]}


# https://secure.conscribo.nl/sib-utrecht/?module=entityOverview&groupId=7
entity_group_uitschrijving_aangevraagd = get_group_members_cached("7")

# https://secure.conscribo.nl/sib-utrecht/?module=entityOverview&groupId=14
donateurs = get_group_members_cached("14")

# https://secure.conscribo.nl/sib-utrecht/?module=entityOverview&groupId=13
externen = get_group_members_cached("13")

# https://secure.conscribo.nl/sib-utrecht/?module=entityOverview&groupId=19
overige_externen_voor_incassos = get_group_members_cached("19")

wil_geen_email_van_ons_ontvangen = get_group_members_cached(
    group_wil_geen_email_van_ons_ontvangen
)

groups = {
    "donateurs": donateurs,
    "externen": externen,  # donateurs and overige externen are also contained in this group
    "overige_externen_voor_incassos": overige_externen_voor_incassos,
    "uitschrijving_aangevraagd": entity_group_uitschrijving_aangevraagd,
    "wil_geen_email_van_ons_ontvangen": wil_geen_email_van_ons_ontvangen,
}

# print(json.dumps(entity_groups, indent=2))


def list_filter_raw(fieldNames, filters):
    """
    List relations with the given field names and filters.

    Filters can be for example:

    .. code-block:: python
       [{
           "fieldName": "code",
           "operator": "=",
           "value": [329],  # Vincent
       }]

    See https://www.conscribo.nl/APIDocs/#?route=post-/relations/filters/
    """
    return conscribo_post(
        f"/relations/filters/",
        json={
            "requestedFields": fieldNames,
            "filters": filters,
        },
    )


def get_block_email_members():
    return get_group_members(group_wil_geen_email_van_ons_ontvangen)


# ans_canonical = dict()
# for entry in ans.i


def relation_to_canonical(relation):
    canonical = dict()

    to_canonical = canonical_key.get_conscribo_to_key()

    flattened_relation = flatten_dict(relation)

    for key, value in flattened_relation.items():
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


def relation_to_canonical_alumnus(relation):
    canonical = dict()
    to_canonical = canonical_key.get_conscribo_alumnus_to_key()

    flattened_relation = flatten_dict(relation)

    for key, value in flattened_relation.items():
        new_key = to_canonical.get(key, None)

        if new_key is not None:
            canonical[new_key] = value
            continue

        other = canonical.setdefault("other", dict())
        other[key] = value

    # pronouns = canonical.get("pronouns", None)
    # if pronouns is not None and isinstance(pronouns, int):
    #     pronouns = {
    #         0: None,
    #         1: "hij/hem",
    #         2: "zij/haar",
    #         4: "die/diens",
    #         8: "anders:",
    #     }.get(pronouns, pronouns)
    #     canonical["pronouns"] = pronouns

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
        },
    )

    print("\n\n")


def list_relations_persoon():
    fieldDefinitions = conscribo_get(f"/relations/fieldDefinitions/persoon")["fields"]

    fieldNames = [field["fieldName"] for field in fieldDefinitions]

    # print(f"Field definitions: {fieldDefinitions}")

    result = conscribo_post(
        "/relations/filters/",
        json={
            "entityType": "persoon",
            "requestedFields": fieldNames,
            "filters": [
                # {
                #     "fieldName": "code",
                #     "operator": "=",
                #     "value": [329],  # Vincent
                # }
            ],
        },
    )

    relations = [
        relation_to_canonical(relation) for relation in result["relations"].values()
    ]

    return relations


def list_relations_members():
    personen = list_relations_persoon()

    members = [person for person in personen if int(person["conscribo_id"]) < 2000]

    return members


def list_relations_alumnus():
    fieldDefinitions = conscribo_get(f"/relations/fieldDefinitions/re__nisten")[
        "fields"
    ]

    fieldNames = [field["fieldName"] for field in fieldDefinitions]

    result = conscribo_post(
        "/relations/filters/",
        json={
            "entityType": "re__nisten",
            "requestedFields": fieldNames,
            "filters": [
                # {
                #     "fieldName": "code",
                #     "operator": "=",
                #     "value": [329],  # Vincent
                # }
            ],
        },
    )

    relations = [
        relation_to_canonical_alumnus(relation)
        for relation in result["relations"].values()
    ]

    return relations
