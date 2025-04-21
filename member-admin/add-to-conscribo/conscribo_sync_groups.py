import keyring.credentials
import requests
import json
import keyring
from getpass import getpass
import canonical_key
import conscribo_auth
from conscribo_auth import conscribo_post, conscribo_get
from conscribo_list_relations import list_relations_persoon, get_group_members, update_relation
from time import sleep

ans = conscribo_get(
    f"/relations/groups/"
)

with open("conscribo_groups.json", "w") as f:
    json.dump(ans, f, indent=2)
