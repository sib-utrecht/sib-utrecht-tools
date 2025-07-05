import keyring.credentials
import requests
import json
import keyring
from getpass import getpass
from ..canonical import canonical_key
from . import auth
from .auth import conscribo_post, conscribo_get
from .list_relations import list_relations_persoon, get_group_members, update_relation
from time import sleep

auth.do_auth()

# print(json.dumps(conscribo_get(
#         f"/relations/fieldDefinitions/persoon"
# ), indent=2))

# https://secure.conscribo.nl/sib-utrecht/?module=entityOverview&groupId=7
entity_group_uitschrijving_aangevraagd = get_group_members("7")

# print(json.dumps(list(entity_group_uitschrijving_aangevraagd), indent=2))

# https://secure.conscribo.nl/sib-utrecht/?module=entityOverview&groupId=14
donateurs = get_group_members("14")

# https://secure.conscribo.nl/sib-utrecht/?module=entityOverview&groupId=13
externen = get_group_members("13")

# https://secure.conscribo.nl/sib-utrecht/?module=entityOverview&groupId=19
overige_externen_voor_incassos = get_group_members("19")

groups = {
    "donateurs": donateurs,
    "externen": externen,  # donateurs and overige externen are also contained in this group
    "overige_externen_voor_incassos":
        overige_externen_voor_incassos,
}

print(json.dumps({k: ",".join(v) for (k,v) in groups.items()}, indent=2))

# print(json.dumps(entity_group_uitschrijving_aangevraagd, indent=2))
print("\n\n")

# result = requests.post(
#     f"{api_url}/relations/filters/",
#     headers={
#         "X-Conscribo-SessionId": session_id,
#         "X-Conscribo-API-Version": "1.20240610",
#     },
#     json={
#         "requestedFields": fieldNames,
#         "filters": [
#             # {
#             #     "fieldName": "code",
#             #     "operator": "=",
#             #     "value": [329],  # Vincent
#             # }
#         ]
#     },
# )

# print(result)
# print(result.ok)

# ans = result.json()
# print(json.dumps(ans, indent=2))


# relations_dict : dict = ans["relations"]
# relations : list[dict] = relations_dict.values()

relations = list_relations_persoon()

# with open("conscribo_leden_en_externen_2025-04-17_1255.json", "w") as f:
#     json.dump(relations, f, indent=2)

exit(0)


pronouns_map = dict()

for relation in relations:
    conscribo_id = relation["conscribo_id"]

    expected_member = int(relation["conscribo_id"]) < 2000
    in_groups = [
        group_name
        for group_name, group_members in groups.items()
        if conscribo_id in group_members
    ]

    # if expected_member != (len(in_groups) == 0):
    #     print(
    #         f"For {relation['other']['selector']}:\n"
    #         f"  Expected member: {expected_member}\n"
    #         f"  In groups: {in_groups}\n")
    #     continue

    # continue

    if int(relation["conscribo_id"]) >= 2000:
        continue

    if len(in_groups) > 0:
        continue

    
    selector_name = relation["other"]["selector"]
    pronouns = relation.get("pronouns", None) or ""
    aanhef = relation["other"]["aanhef"]

    if conscribo_id in [150]:
        continue

    # if aanhef != "Dhr.":
    #     continue

    if len(pronouns) == 0:
        if aanhef == "Dhr.":
            pronouns = "he/him"
        elif aanhef == "Mevr.":
            pronouns = "she/her"

        print(f"Updating pronouns of {selector_name} to {pronouns}")

        update_relation({
            "conscribo_id": conscribo_id,
            "pronouns": pronouns,
        })

        sleep(2)
        # break

    # print(f"{selector_name:<26} | {aanhef:<5} | {repr(pronouns)}")
    # pronouns_map[relation["conscribo_id"]] = pronouns


    # print("\n")
    # print(json.dumps(canonical, indent=2))
    # print("\n\n")

# print(json.dumps(pronouns_map, indent=2))

