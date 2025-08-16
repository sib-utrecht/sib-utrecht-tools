import argparse
from argparse import ArgumentParser, Namespace
import sys
from sib_tools.conscribo.relations import list_relations_alumnus, list_relations_members, list_relations_active_members
import json
import beaupy
from unidecode import unidecode
from time import sleep
from datetime import datetime, date, timezone


from sib_tools.conscribo.finance import (
    list_conscribo_transactions,
    list_conscribo_accounts,
)
from sib_tools.conscribo.list_accounts import (
    show_choose_account,
    print_list_accounts,
    build_account_options,
)
from sib_tools.google.auth import (
    list_groups_directory_api,
    list_groups_settings_api,
    list_group_members_api,
)


#  ./sib-tools.sh list conscribo-transactions 2025-01-01 2025-07-07


def handle_list_alumnus(args: Namespace):
    alumni = list_relations_alumnus()
    if args.conscribo_id:
        filtered = [
            a for a in alumni if str(a.get("conscribo_id")) == str(args.conscribo_id)
        ]
        print(json.dumps(filtered, indent=2))
    else:
        print(json.dumps(alumni, indent=2))
        print()


def handle_list_members(args: Namespace):
    members = list_relations_members()
    if args.conscribo_id:
        filtered = [
            m for m in members if str(m.get("conscribo_id")) == str(args.conscribo_id)
        ]
        print(json.dumps(filtered, indent=2))
    else:
        print(json.dumps(members, indent=2))
        print()


def handle_list_education(args: Namespace):
    """List educational institution counts among members."""
    active_date = args.date or date.today().isoformat()

    print(f"Showing educational institution counts for active members as of {active_date}")

    # members = list_relations_members()
    members = list_relations_active_members(date=active_date)

    # Count occurrences of educational institutions
    education_counts = {}
    total_members = len(members)

    institution_mapper = {
        "UU": "Universiteit Utrecht",
        "HKU": "Hogeschool voor de Kunsten Utrecht",
        "HU": "Hogeschool Utrecht",
        "Utrecht University": "Universiteit Utrecht",
        "Graduate School Life Science": "Universiteit Utrecht",
        "Hogeschool van de Kunsten Utrecht": "Hogeschool voor de Kunsten Utrecht",
    }

    for member in members:
        education = member.get("educational_institution") or "(empty)"
        education = institution_mapper.get(education, education)
        member["institution"] = education

        education_counts[education] = education_counts.get(education, 0) + 1

    # Sort by count (descending) then by name
    sorted_education = sorted(education_counts.items(), key=lambda x: (-x[1], x[0]))

    print(f"Educational Institution Statistics")
    print(f"=================================")
    print(f"Total members: {total_members}")
    print(f"Unique educational institutions: {len(education_counts)}")
    print()

    if args.raw:
        # Print raw JSON output
        result = {
            "total_members": total_members,
            "unique_institutions": len(education_counts),
            "institution_counts": dict(sorted_education),
        }
        print(json.dumps(result, indent=2))
    elif args.csv:
        # Print CSV output for spreadsheet analysis
        print("Educational Institution,Count,Percentage")
        for institution, count in sorted_education:
            percentage = (count / total_members) * 100
            # Escape commas in institution names by quoting
            institution_escaped = f'"{institution}"' if ',' in institution else institution
            print(f"{institution_escaped},{count},{percentage:.1f}")
        
        # If --list-people is also specified, print detailed member information
        if args.list_people:
            print()
            columns = ["institution", "number", "first_name", "last_name", "date_of_birth", "study"]
            print(",".join(columns))
            
            # Create a list of members with their institutions for sorting
            members_with_institutions = []
            for member in members:
                institution = member.get("institution") or "(empty)"
                first_name = member.get("first_name") or ""
                last_name = member.get("last_name") or ""
                date_of_birth = member.get("date_of_birth") or ""
                study = member.get("study") or ""
                
                members_with_institutions.append({
                    "institution": institution,
                    "first_name": first_name,
                    "last_name": last_name,
                    "date_of_birth": date_of_birth,
                    "study": study,
                    "institution_count": education_counts[institution]
                })
            
            # Sort by institution count (descending), then by first name (ascending, diacritics removed)
            members_with_institutions.sort(
                key=lambda x: (
                    -x["institution_count"],
                    unidecode(x["first_name"]).lower(),
                    unidecode(x["last_name"]).lower()
                )
            )
            
            # Print the CSV data
            institution_group = None
            count_for_institution = 0

            for member in members_with_institutions:
                institution = member.get("institution")

                if institution != institution_group:
                    count_for_institution = 0
                    institution_group = institution

                count_for_institution += 1

                member["number"] = count_for_institution
                
                data = [
                    member.get(col, "")
                    for col in columns
                ]

                for k, v in list(enumerate(data)):
                    v = str(v or "")
                    # Escape any quotes
                    v = v.replace('"', '""')

                    # Escape any commas in the data by quoting
                    if ',' in v or '"' in v:
                        v = f'"{v}"'
                    data[k] = v

                print(",".join(data))

    else:
        # Print formatted output
        print("Educational Institution Counts:")
        print("--------------------------------")
        for institution, count in sorted_education:
            percentage = (count / total_members) * 100
            print(f"{institution}: {count} ({percentage:.1f}%)")

    print()


def handle_list_accounts(args: Namespace):
    print_list_accounts(
        date=args.date,
        raw=args.raw,
    )


def handle_list_transactions(args: Namespace):
    account_id = args.account_id
    if not account_id:
        answer = beaupy.confirm(
            "No account ID supplied. Would you like to select one interactively?"
        )
        if answer:
            account_id = show_choose_account(args.start_date)
            if not account_id:
                print("No account selected. Exiting.")
                return
    print(
        f"Listing Conscribo transactions from {args.start_date} to {args.end_date} for account {account_id}"
    )
    transactions = list_conscribo_transactions(
        args.start_date,
        args.end_date,
        account_id,
        limit=args.limit,
        offset=args.offset,
    )
    print(json.dumps(transactions, indent=2))
    print(
        f"Showing filter results {args.offset + 1} to {args.offset + len(transactions)}"
    )
    if len(transactions) == args.limit:
        print(
            f"Use --offset {args.offset + args.limit} to get the next page of results."
        )
    else:
        print("No more results available.")


def handle_list_balance_diff(args: Namespace):
    print(f"Calculating balance difference from {args.start_date} to {args.end_date}")
    debet_per_account = dict()
    credit_per_account = dict()
    account_id = None
    fetch_date = datetime.now(timezone.utc).isoformat()

    offset = 0
    limit = 100
    while True:
        transactions = list_conscribo_transactions(
            args.start_date,
            args.end_date,
            account_id,
            limit=limit,
            offset=offset,
        )["transactions"].values()

        for tx in transactions:
            transactionId = tx["transactionId"]
            date = tx["date"]
            tx_description = tx.get("description", "")

            for rowId, row in tx.get("transactionRows", {}).items():
                account = row["accountNr"]
                row_description = row.get("description", "")

                if row["side"] == "debet":
                    debet_per_account[account] = debet_per_account.get(
                        account, 0
                    ) + float(row["amount"])
                elif row["side"] == "credit":
                    credit_per_account[account] = credit_per_account.get(
                        account, 0
                    ) + float(row["amount"])

        if len(transactions) < limit:
            print("No more transactions available.")
            break

        offset += limit
        print(f"Processed {offset} transactions")
        sleep(1)

    if args.output:
        print(f"Storing results to {args.output}...")
        with open(args.output, "w") as f:
            json.dump(
                {
                    "fetch_date": fetch_date,
                    "from_date": args.start_date,
                    "to_date": args.end_date,
                    "debet_per_account": debet_per_account,
                    "credit_per_account": credit_per_account,
                },
                f,
                indent=2,
            )
        print("Results stored to balance_diff.json")

    if args.raw:
        print(
            json.dumps(
                {
                    "fetch_date": fetch_date,
                    "from_date": args.start_date,
                    "to_date": args.end_date,
                    "debet_per_account": debet_per_account,
                    "credit_per_account": credit_per_account,
                },
                indent=2,
            )
        )
        return

    accounts = list_conscribo_accounts(date=args.end_date or args.start_date or None)[
        "accounts"
    ]

    # Print a tree with the details
    tree = build_account_options(accounts)

    included_accounts = set()
    for accountNr, label, prefix in tree:
        credit = credit_per_account.get(accountNr, 0)
        debet = debet_per_account.get(accountNr, 0)
        print(f"{label}")
        # Put credit in green, debet in red
        if credit != 0 or debet != 0:
            line = prefix + "     = "
            if debet == 0:
                line += "\x1b[37m   -  \x1b[0m"
            else:
                line += f"\x1b[31m€ {debet:.2f}\x1b[0m"

            if credit == 0:
                line += " | \x1b[37m  -  \x1b[0m"
            else:
                line += f" | \x1b[32m€ {credit:.2f}\x1b[0m"

            print(line)
            print(prefix)
        included_accounts.add(accountNr)

    # print(f"Debet per account keys: {json.dumps(list(debet_per_account.keys()))}")
    # print(f"Credit per account keys: {json.dumps(list(credit_per_account.keys()))}")
    # print(f"Included accounts: {json.dumps(list(included_accounts))}")

    orphaned_accounts = (
        set(debet_per_account.keys()) | set(credit_per_account.keys())
    ) - included_accounts

    for orphaned_account in orphaned_accounts:
        print(
            f"{orphaned_account} | € {debet_per_account.get(orphaned_account, 0):.2f} debet | € {credit_per_account.get(orphaned_account, 0):.2f} credit"
        )

    total_credit = sum(credit_per_account.values())
    total_debet = sum(debet_per_account.values())

    print(f"Total | € {total_debet:.2f} debet | € {total_credit:.2f} credit")
    print("Done")


def handle_list_google_groups_directory(args: Namespace):
    """List Google Groups using the Directory API and print as JSON."""
    groups = list_groups_directory_api()
    print(json.dumps(groups, indent=2))
    print()


def handle_list_google_groups_settings(args: Namespace):
    """List Google Groups using the Groups Settings API and print as JSON."""
    groups = list_groups_settings_api()
    print(json.dumps(groups, indent=2))
    print()


def handle_list_google_groups_members(args: Namespace):
    emails = args.email or ["members@sib-utrecht.nl", "alumni@sib-utrecht.nl"]
    if isinstance(emails, str):
        emails = [emails]

    for email in emails:
        print(f"For {email}:")
        members = list_group_members_api(email)
        if args.raw:
            print(json.dumps(members, indent=2))
        else:
            if not members:
                print("  (no members)")
            for m in members:
                address = m.get("email", "?")
                role = m.get("role", "?").lower()
                type_ = m.get("type", "?").lower()

                # if role == "member" and type_ == "user":
                #     print(f" - {address}")
                #     continue
                print(f" - {address} ({role}, {type_})")
        print()
    print()


def handle_list_google_contacts(args: Namespace):
    """
    List Google Contacts with a specific label.
    """
    from sib_tools.google.contacts import list_google_contacts, GOOGLE_CONTACTS_MEMBER_LABEL

    label = args.label or GOOGLE_CONTACTS_MEMBER_LABEL
    limit = args.limit if args.limit is not None else None
    offset = args.offset if args.offset is not None else 0
    raw = args.raw

    contacts = list_google_contacts(
        label_name=label, raw=raw, limit=limit, offset=offset
    )
    print(json.dumps(contacts, indent=2))
    print()


def add_parse_args(parser: ArgumentParser):
    parser.set_defaults(func=lambda args: parser.print_help())
    subparser = parser.add_subparsers(
        description="What resource to list members from", dest="resource"
    )
    alumnus_parser = subparser.add_parser(
        "conscribo-alumnus", help="List Conscribo alumni"
    )
    alumnus_parser.add_argument(
        "--conscribo-id",
        type=str,
        required=False,
        help="Conscribo ID of the alumnus to query",
    )
    alumnus_parser.set_defaults(func=handle_list_alumnus)

    members_parser = subparser.add_parser(
        "conscribo-members", help="List Conscribo members"
    )
    members_parser.add_argument(
        "--conscribo-id",
        type=str,
        required=False,
        help="Conscribo ID of the member to query",
    )
    members_parser.set_defaults(func=handle_list_members)

    education_parser = subparser.add_parser(
        "conscribo-education", help="List educational institution counts among members"
    )
    education_parser.add_argument(
        "--raw",
        action="store_true",
        help="If set, print raw JSON output instead of formatted counts",
    )
    education_parser.add_argument(
        "--csv",
        action="store_true",
        help="If set, print output in CSV format for spreadsheet analysis",
    )
    education_parser.add_argument(
        "--date",
        type=str,
        required=False,
        help="Date at which the member needed to be active (default: today) (YYYY-MM-DD)",
    )
    education_parser.add_argument(
        "--list-people",
        action="store_true",
        help="When combined with --csv, also print detailed member information",
    )
    education_parser.set_defaults(func=handle_list_education)

    accounts_parser = subparser.add_parser(
        "conscribo-accounts", help="List Conscribo accounts for a given date"
    )
    accounts_parser.add_argument(
        "--date",
        type=str,
        required=False,
        help="Date for which to list accounts (YYYY-MM-DD)",
    )
    accounts_parser.add_argument(
        "--raw",
        action="store_true",
        help="If set, print raw JSON output instead of a formatted tree",
    )
    accounts_parser.set_defaults(func=handle_list_accounts)

    transactions_parser = subparser.add_parser(
        "conscribo-transactions",
        help="List Conscribo transactions for an account and date range",
    )
    transactions_parser.add_argument(
        "start_date", type=str, help="Start date (YYYY-MM-DD)"
    )
    transactions_parser.add_argument("end_date", type=str, help="End date (YYYY-MM-DD)")
    transactions_parser.add_argument("--account-id", type=str, help="Account ID")
    transactions_parser.add_argument(
        "--limit", type=int, help="Limit the number of transactions returned"
    )
    transactions_parser.add_argument(
        "--offset", type=int, default=0, help="Offset for pagination (default: 0)"
    )
    transactions_parser.set_defaults(func=handle_list_transactions)

    balance_diff_parser = subparser.add_parser(
        "conscribo-balance-diff",
        help="List the difference in balance between two dates for a given account",
    )
    balance_diff_parser.add_argument(
        "start_date", type=str, help="Start date (YYYY-MM-DD)"
    )
    balance_diff_parser.add_argument("end_date", type=str, help="End date (YYYY-MM-DD)")
    balance_diff_parser.add_argument(
        "--raw",
        action="store_true",
        help="If set, print raw JSON output instead of a formatted tree",
    )
    balance_diff_parser.add_argument(
        "--output",
        type=str,
        required=False,
        default=None,
        help="Output file to store the balance difference results",
    )
    # balance_diff_parser.add_argument(
    #     "--account-id",
    #     type=str,
    #     required=False,
    #     help="Account ID to calculate the balance difference for",
    # )
    balance_diff_parser.set_defaults(func=handle_list_balance_diff)

    google_groups_dir_parser = subparser.add_parser(
        "google-groups-directory", help="List Google Groups using Directory API"
    )
    google_groups_dir_parser.set_defaults(func=handle_list_google_groups_directory)

    google_groups_settings_parser = subparser.add_parser(
        "google-groups-settings", help="List Google Groups using Groups Settings API"
    )
    google_groups_settings_parser.set_defaults(func=handle_list_google_groups_settings)

    google_groups_members_parser = subparser.add_parser(
        "google-groups-members", help="List members of one or more Google Groups"
    )
    google_groups_members_parser.add_argument(
        "--email",
        nargs="*",
        help="Email(s) of the Google Group(s) to list members for. If omitted, lists members@sib-utrecht.nl and alumni@sib-utrecht.nl by default.",
    )
    google_groups_members_parser.add_argument(
        "--raw",
        action="store_true",
        help="If set, print raw JSON output instead of formatted lines.",
    )
    google_groups_members_parser.set_defaults(func=handle_list_google_groups_members)

    google_contacts_parser = subparser.add_parser(
        "google-contacts",
        help="List Google Contacts with a specific label",
    )
    google_contacts_parser.add_argument(
        "--label",
        type=str,
        required=False,
        help="Label to filter contacts by",
    )
    google_contacts_parser.add_argument(
        "--raw",
        action="store_true",
        help="If set, print raw JSON output instead of canonicalized contacts.",
    )
    google_contacts_parser.add_argument(
        "--limit", type=int, required=False, help="Limit the number of contacts shown."
    )
    google_contacts_parser.add_argument(
        "--offset",
        type=int,
        required=False,
        default=0,
        help="Offset for pagination (default: 0)",
    )
    google_contacts_parser.set_defaults(func=handle_list_google_contacts)

    return parser
