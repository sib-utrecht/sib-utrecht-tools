import argparse
from argparse import ArgumentParser, Namespace
import sys
from sib_tools.conscribo.relations import list_relations_alumnus
import json
import beaupy
from time import sleep
from datetime import datetime, timezone

from sib_tools.conscribo.finance import (
    list_conscribo_transactions,
    list_conscribo_accounts,
)
from sib_tools.conscribo.list_accounts import (
    show_choose_account,
    print_list_accounts,
    build_account_options,
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
    
    accounts = list_conscribo_accounts(date=args.end_date or args.start_date or None)["accounts"]

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

    orphaned_accounts = (set(debet_per_account.keys()) | set(credit_per_account.keys())) - included_accounts

    for orphaned_account in orphaned_accounts:
        print(f"{orphaned_account} | € {debet_per_account.get(orphaned_account, 0):.2f} debet | € {credit_per_account.get(orphaned_account, 0):.2f} credit")

    total_credit = sum(credit_per_account.values())
    total_debet = sum(debet_per_account.values())

    print(f"Total | € {total_debet:.2f} debet | € {total_credit:.2f} credit")
    print("Done")


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
    return parser
