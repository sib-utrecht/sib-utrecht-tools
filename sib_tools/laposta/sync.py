from ..grist.update_relation_source import set_relation_records_as_source

from .list_members import (
    get_aggregated_relations
)


if __name__ == "__main__":
    # print(json.dumps(laposta_get("/v2/list"), indent=2))
    entries = get_aggregated_relations()
    
    set_relation_records_as_source("Laposta", entries)
