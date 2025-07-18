# import keyring.credentials
import requests
import json
import keyring
# from getpass import getpass
# import canonical_key
# from . import auth
# from .auth import conscribo_post, conscribo_get
# from ..grist.auth import grist_post, grist_patch
from .relations import (
    list_relations_persoon,
    update_relation,
)
from time import sleep
from ..grist.update_relation_source import set_relation_records_as_source, relations_doc


relations = list_relations_persoon()

# relations = [
#     {
#         "conscribo_id": "730",
#         "last_name": "Coolman",
#         "other": {
#             "selector": "730: Vincu Coolman",
#             "rekening.nr": "",
#             "rekening.country": "  ",
#             "rekening.city": "",
#             "aanhef": "Dhr.",
#             "weergavenaam": "Dhr. Vince",
#             "introkamp": "September",
#             "re__nist": 0,
#         },
#         "membership_end": None,
#         "admin_comments": "Ongevalnaam: ...",
#         "date_of_birth": "2000-01-01",
#         "membership_start": "2021-08-16",
#         "email": "test1@vkuhlmann.com",
#         "bank_account_name": "V Kuhlmann",
#         "iban": "NL00000",
#         "bic": "ING",
#         "phone_number": "0610000000",
#         "place": "Utrecht",
#         "house_number_addition": "",
#         "postal_code": "3584CC",
#         "street": "Princetonplein",
#         "house_number_decimal": "9",
#         "first_name": "Vincent",
#         "admin_committees_comment": "aaaaa",
#         "educational_institution": "Universiteit Utrecht",
#         "study": "Wiskunde en Natuurkunde",
#         "requested_deregistration": 0,
#         "learn_about_sib": "internet",
#         "pronouns": "hij/hem",
#     }
# ]

def add_relation_type1(rel):
    if int(rel["conscribo_id"]) < 2000:
        rel["relation_type"] = "Member"
    else:
        rel["relation_type"] = "External"

    return rel

relations = [
    add_relation_type1(a)
    for a in relations
]

# for relation in relations:
#     conscribo_id = relation["conscribo_id"]

#     expected_member = int(relation["conscribo_id"]) < 2000
#     if not expected_member:
#         continue


# grist_post(
#     f"/docs/{relations_doc}/tables/Members/records",
#     body={
#         "records": [
#             {
#                 "fields": {
#                     "id": 83,
#                     "email": "bbbbb@example.org",
#                     "first_name": "Bbbb",
#                 }
#             }
#         ],
#     },
# )


# grist_patch(
#     f"/docs/{relations_doc}/tables/Members/records",
#     body={
#         "records": [
#             {
#                 "id": 2,
#                 "fields": {
#                     # "id": 83,
#                     "email": "bbbbb@example.org",
#                     "first_name": "Bbbb",
#                 }
#             }
#         ],
#     },
# )

# exit(0)

set_relation_records_as_source("Conscribo", relations)

# set_relation_records_as_source("Members", [
    # {
    #     # "conscribo_id": int(relation["conscribo_id"]),
    #     # "first_name": relation["first_name"],
    #     # "last_name": relation["last_name"],
    #     # "email": relation["email"],
    #     relation
    # }
    # for relation in relations
# ])


