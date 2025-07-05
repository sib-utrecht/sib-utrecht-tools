from laposta_auth import laposta_get, laposta_post, laposta_patch, laposta_delete
import json
from ..canonical import canonical_key
from ..canonical.canonical_key import flatten_dict
from time import sleep
from ..grist.grist_update_relation_source import set_relation_records_as_source

from .list_members import (
    account_id,
    member_birthday_list_id,
    member_newsletter_list_id,
    alumni_birthday_list_id,
    test_list_id,
    get_list_members,
    relation_to_canonical,
    get_aggregated_relations
)


if __name__ == "__main__":
    # print(json.dumps(laposta_get("/v2/list"), indent=2))
    entries = get_aggregated_relations()
    
    set_relation_records_as_source("Laposta", entries)
