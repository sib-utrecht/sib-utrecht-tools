from .auth import grist_get, grist_put, grist_post
from .constants import relations_doc
import json
import datetime
from time import sleep

table_name = ""

# orgs = grist_get("/orgs")
# print(orgs)
# print("\n")
# print(json.dumps(orgs))

def main():

    recs = grist_get(f"/docs/{relations_doc}/tables/Laposta/records")
    print(json.dumps(recs, indent=2))

    # exit(0)


    records = [
        {
            "email": "test3@example.org",
            "send_birthday": False,
            "send_newsletter": True,
            "newsletter_subscription_state": "active",
            "first_name": "Vincent",
            "last_name": "Coolman",
        },
        {
            "email": "test2@example.org",
            "send_birthday": True,
            "send_newsletter": True,
            "newsletter_subscription_state": "active",
            "date_of_birth": "2024-09-06",
            "birthday_subscription_state": "active",
            "first_name": "Vincu",
            "last_name": "Coolman",
        },
    ]

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
                    # "require": {"sync_state": "Synced"},
                    # "fields": {
                    #     # "requires_update": True,
                    #     "sync_state": "Deleted"
                    # },
                    "require": {},
                    "fields": {"tracked": False},
                },
            ],
        },
    )

    # grist_post(
    #     f"/docs/{relations_doc}/tables/Laposta/records",
    #     body={
    #         "records": [
    #             {
    #                 "fields": {
    #                     "email": "bbbbb@example.org",
    #                     "first_name": "Bbbb",
    #                 }
    #             }
    #         ],
    #     },
    # )
    # exit(0)


    # grist_put(
    #     f"/docs/{relations_doc}/tables/Laposta/records",
    #     query={
    #         "allow_empty_require": "true",
    #         "onmany": "all",
    #         "noadd": "true",
    #     },
    #     body={
    #         "records": [
    #             {
    #                 "require": {"sync_state": "Pending change"},
    #                 "fields": {"sync_state": "Overwritten"},
    #             },
    #         ],
    #     },
    # )

    # sleep(2)

    grist_put(
        f"/docs/{relations_doc}/tables/Laposta/records",
        body={
            "records": [
                {
                    "require": {
                        # "email": record["email"],
                        "synced_as": record["email"],

                        # "modified": ""
                        # "sync_state": "Deleted",
                        "is_synced": True,
                    },
                    "fields": {
                        **record,
                        # "requires_update": False,
                        # "modified": ""
                        # "sync_state": "Synced",
                        "last_synced_at": None,
                        # "last_synced_at": datetime.datetime.now().isoformat(),
                        "tracked": True,
                        # "synced_as": record["email"]
                        # "last_synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        # "last_synced_at": "-"
                    },
                }
                for record in records
            ]
        },
    )

    # sleep(5)

    # grist_put(
    #     f"/docs/{relations_doc}/tables/Laposta/records",
    #     query={
    #         "onmany": "all",
    #         "noadd": "true",
    #     },
    #     body={
    #         "records": [
    #             {
    #                 "require": {"tracked": True},
    #                 "fields": {
    #                     # "last_synced_at": None,
    #                     "last_synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    #                     # "sync_state": "Synced",
    #                 },
    #             }
    #         ]
    #     },
    # )

    # sleep(2)

    # grist_put(
    #     f"/docs/{relations_doc}/tables/Laposta/records",
    #     query={
    #         "onmany": "all",
    #         "noadd": "true",
    #     },
    #     body={
    #         "records": [
    #             {
    #                 "require": {"tracked": True},
    #                 "fields": {
    #                     # "last_synced_at": None,
    #                     "last_synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    #                     # "sync_state": None
    #                 },
    #             }
    #         ]
    #     },
    # )

    # last_synced_at = $last_synced_at
    # if $last_synced_at is None:
    #   return "Pending change"

    # is_synced = ($last_synced_at == "-" or ($last_synced_at - $modified).total_seconds() > -5)
    # tracked = $tracked

    # if tracked and is_synced:
    #   return "Synced"
    
    # if tracked:
    #   return "Pending change"

    # if is_synced and not tracked:
    #   return "Deleted"
    
    # return "Overwritten"




    # Last synced at (on data cleaning):
    # #IF($tracked, NOW(), None)

    # if $tracked:
    #   return NOW()
    
    # return None
    # 
    #



    # grist_put(
    #     f"/docs/{relations_doc}/tables/Laposta/records",
    #     query={
    #         "onmany": "all",
    #     },
    #     body={
    #         "records": [
    #             {
    #                 "require": {
    #                     "requires_update": True
    #                 },
    #                 "fields": {
    #                     "outdated": True
    #                 },
    #             }
    #         ]
    #     },
    # )
