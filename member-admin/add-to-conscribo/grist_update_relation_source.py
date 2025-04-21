from grist_auth import grist_get, grist_put, grist_post
import json
import datetime
from time import sleep
import re

relations_doc = "rYgNbGRQ2pdW"
table_name = ""

force_batch = False

batch_size = 2
batch_interval = 0.05

if force_batch:
    batch_size = 100
    batch_interval = 2


orgs = grist_get("/orgs")
print(orgs)
print("\n")
print(json.dumps(orgs))

def set_relation_records_as_source(table_name : str, records : list[dict]):
    if not re.fullmatch(r"^[a-zA-Z0-9_]+$", table_name):
        raise ValueError(f"Invalid table name {repr(table_name)}")

    # recs = grist_get(f"/docs/{relations_doc}/tables/{table_name}/records")
    # print(json.dumps(recs, indent=2))

    # exit(0)

    # records = [
    #     {
    #         "email": "test3@example.org",
    #         "send_birthday": False,
    #         "send_newsletter": True,
    #         "newsletter_subscription_state": "active",
    #         "first_name": "Vincent",
    #         "last_name": "Coolman",
    #     },
    #     {
    #         "email": "test2@example.org",
    #         "send_birthday": True,
    #         "send_newsletter": True,
    #         "newsletter_subscription_state": "active",
    #         "date_of_birth": "2024-09-06",
    #         "birthday_subscription_state": "active",
    #         "first_name": "Vincu",
    #         "last_name": "Coolman",
    #     },
    # ]

    print(f"Amount of records to sync to {table_name}: {len(records)}")

    grist_put(
        f"/docs/{relations_doc}/tables/Laposta/records",
        query={
            "allow_empty_require": "true",
            "onmany": "all",
            "noadd": "true",
        },
        body={
            "records": [
                {
                    "require": {},
                    "fields": {"tracked": False},
                },
            ],
        },
    )

    sleep(2)

    nextrecords = records
    while True:
        records = nextrecords[:batch_size]
        if len(records) == 0:
            break

        nextrecords = nextrecords[batch_size:]

        grist_put(
            f"/docs/{relations_doc}/tables/Laposta/records",
            body={
                "records": [
                    {
                        "require": {
                            "synced_as": record["email"],
                            "is_synced": True,
                        },
                        "fields": {
                            **record,
                            # "last_synced_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
                            # This value will normally be overwritten by the server.
                            # In case the server is overloaded, this value is still used
                            "last_synced_at": "2050-01-01T00:00Z",
                            "modified": "2025-01-01T00:00Z",
                            "tracked": True,
                        },
                    }
                    for record in records
                ]
            },
        )
        # sleep(0.05)
        # sleep(0.5)
        sleep(2)