import requests
import json
import conscribo_auth
from conscribo_auth import conscribo_post, conscribo_get
from conscribo_list_relations import list_relations_persoon, list_relations_alumnus, get_group_members, update_relation
from time import sleep


relations = list_relations_alumnus()

print(json.dumps(relations, indent=2))

