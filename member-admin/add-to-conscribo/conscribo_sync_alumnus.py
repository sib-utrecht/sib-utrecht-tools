import requests
import json
# from getpass import getpass
# import canonical_key
# import conscribo_auth
# from conscribo_auth import conscribo_post, conscribo_get
# from grist_auth import grist_post, grist_patch
from conscribo_list_relations import (
    list_relations_alumnus,
    get_group_members,
    update_relation,
)
from grist_update_relation_source import set_relation_records_as_source, relations_doc


relations = list_relations_alumnus()

def add_relation_type2(rel):
    rel["relation_type"] = "Alumnus"
    return rel

relations = [
    add_relation_type2(a)
    for a in relations
]
set_relation_records_as_source("ConscriboAlumni", relations)
