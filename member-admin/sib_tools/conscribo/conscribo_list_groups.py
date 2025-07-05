import keyring.credentials
import requests
import json
import keyring
from getpass import getpass
from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict

from . import conscribo_auth
from .conscribo_auth import conscribo_post, conscribo_get, conscribo_patch

from .conscribo_list_relations import entity_groups

def list_entity_groups():
    return entity_groups


