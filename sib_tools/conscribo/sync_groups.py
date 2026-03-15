from typing import Any
from .auth import conscribo_get
from ..grist.auth import grist_get, relations_doc
# from ..grist.list import relations_doc
from uuid import uuid4


table_name = "Conscribo_Memberships"


records : list[dict[str, Any]] = grist_get(
    f"/docs/{relations_doc}/tables/{table_name}/records")["records"]


ans = conscribo_get(
    "/relations/groups/"
)
entity_groups = ans["entityGroups"]


lookup_dict = {
    f"{record['Group_id']}:{record['Conscribo_id']}": record
    for i, record in enumerate(records)
}

up_to_date_token = str(uuid4())

to_add: list[dict[str, object]] = []
to_remove: list[dict[str, object]] = []

for group in entity_groups:
    group_id = group["id"]
    group_name = group["name"]

    for member in group["members"]:
        entity_id = member["entity_id"]

        existing_record = lookup_dict.get(f"{group_id}:{entity_id}", None)

        if existing_record is None:
            to_add.append({
                "Group_id": group_id,
                "Conscribo_id": entity_id,
                # "is_tracked": True
            })
            continue

        existing_record["up_to_date_token"] = up_to_date_token


for record in records:
    if record.get("up_to_date_token", None) == up_to_date_token:
        continue

    to_remove.append(record)


# grist_post(
#     f"/docs/{relations_doc}/tables/{table_name}/records",
#     body={
#         "records
# )








# with open("conscribo_groups.json", "w") as f:
#     json.dump(ans, f, indent=2)
