from grist_auth import grist_get, grist_put, grist_post
import json

relations_doc = "rYgNbGRQ2pdW"
table_name = ""

orgs = grist_get("/orgs")
print(orgs)
print("\n")
print(json.dumps(orgs))

recs = grist_get(f"/docs/{relations_doc}/tables/Laposta/records")
print(json.dumps(recs, indent=2))

# exit(0)

records = [
    {
        "email": "vincent.kuhlmann+test@hotmail.com",
        "send_birthday": False,
        "send_newsletter": True,
        "newsletter_subscription_state": "active",
        "first_name": "Vincent",
        "last_name": "Coolman",
    },
    {
        "email": "secretaris@sib-utrecht.nl",
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
    query={"allow_empty_require": "true"},
    body={
        "records": [
            {
                "require": dict(),
                "fields":
                {
                    "requires_update": "true",
                },
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


grist_put(
    f"/docs/{relations_doc}/tables/Laposta/records",
    body={
        "records": [
            {
                "require": {
                    "email": record["email"],
                    # "modified": ""
                },
                "fields": {
                    "first_name": "Aaaa"
                    # **record,
                    # "modified": ""
                },
            }
            for record in records
        ]
    },
)
