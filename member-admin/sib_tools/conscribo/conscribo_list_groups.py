import keyring.credentials
import requests
import json
import keyring
from getpass import getpass
from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict

from . import conscribo_auth
from .conscribo_auth import conscribo_post, conscribo_get, conscribo_patch, conscribo_delete

from .conscribo_list_relations import entity_groups

def list_entity_groups():
    return entity_groups

def add_relations_to_group(
    group_id : int,
    user_ids : list[str],
):
    return conscribo_post(
        f"/relations/groups/{group_id}/members/",
        json={
            "relationIds": user_ids
        },
    )

def remove_relations_from_group(
    group_id : int,
    user_ids : list[str],
):
    return conscribo_delete(
        f"/relations/groups/{group_id}/members/",
        data={
            "relationIds": user_ids
        },
    )


