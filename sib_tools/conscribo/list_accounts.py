import json
import beaupy  # pyright: ignore[reportMissingTypeStubs]
from typing import cast

from sib_tools.conscribo.finance import (
    list_conscribo_accounts,
)
from sib_tools.conscribo.types import ConscriboAccount, ConscriboAccountsResponse

# def print_account_tree(accounts: list[dict], parent_id: str = None, prefix: str = ""):
#     # Find all children of the current parent
#     children = [a for a in accounts if a.get("parent") == parent_id]
#     total = len(children)
#     for idx, account in enumerate(children):
#         is_last = idx == (total - 1)
#         branch = "└── " if is_last else "├── "
#         print(prefix + branch + f"{account['accountNr']}: {account['accountName']}")
#         # Prepare the prefix for the next level
#         next_prefix = prefix + ("     " if is_last else "│    ")
#         print_account_tree(accounts, account["accountNr"], next_prefix)

def build_account_options(
    accounts: list[ConscriboAccount],
    parent_id: str | None = None,
    prefix: str = "",
) -> list[tuple[str, str, str]]:
    options: list[tuple[str, str, str]] = []
    children = [a for a in accounts if a.get("parent") == parent_id]
    total = len(children)
    for idx, account in enumerate(children):
        account_nr = account.get("accountNr")
        if not account_nr:
            continue
        account_name = account.get("accountName") or ""

        is_last = idx == (total - 1)
        branch = "└── " if is_last else "├── "
        label = prefix + branch + f"{account_nr}: {account_name}"
        next_prefix = prefix + ("     " if is_last else "│    ")
        options.append((account_nr, label, next_prefix))
        options += build_account_options(accounts, account_nr, next_prefix)
    return options

def print_account_tree(accounts: list[ConscriboAccount], parent_id: str | None = None, prefix: str = "") -> None:
    """
    Print a tree structure of accounts.
    """
    options = build_account_options(accounts, parent_id, prefix)
    for _account_id, label, _ in options:
        print(label)
    if not options:
        print(prefix + "No accounts found.")

def show_choose_account_tall(date : str|None) -> str | None:
    # This version can cause problems because of being too tall for the terminal.

    # Fetch accounts for selection
    # ans = list_conscribo_accounts(getattr(args, 'date', None))
    ans = list_conscribo_accounts(date=date)
    accounts = ans["accounts"]
    # Build a flat list of account options for selector

    options = build_account_options(accounts)
    labels = [label for _, label, _ in options]
    selected = cast(str | None, beaupy.select(labels, cursor_style="fg:#00ff00 bold", cursor="➤ "))
    if selected is not None:
        idx = labels.index(selected)
        account_id = options[idx][0]
        return str(account_id)

    print("No account selected. Exiting.")
    return None


def show_choose_account(date: str | None) -> str | None:
    """
    Interactive account selector with navigation through account levels.
    """
    ans = list_conscribo_accounts(date=date)
    accounts = ans["accounts"]

    # Build a lookup for children and parents
    from collections import defaultdict
    children_map: defaultdict[str | None, list[ConscriboAccount]] = defaultdict(list)
    parent_map: dict[str, str | None] = {}
    for acc in accounts:
        parent = acc.get("parent")
        account_nr = acc.get("accountNr")
        if not account_nr:
            continue
        children_map[parent].append(acc)
        parent_map[account_nr] = parent

    current_parent: str | None = None
    path: list[str] = []
    while True:
        current_accounts = children_map.get(current_parent, [])
        options: list[tuple[str, str, bool]] = []
        for acc in current_accounts:
            account_nr = acc.get("accountNr")
            if not account_nr:
                continue
            account_name = acc.get("accountName") or ""

            # Mark if this account has children
            has_children = len(children_map.get(account_nr, [])) > 0
            label = f"{account_nr}: {account_name}"
            if has_children:
                label += " [>]"
            options.append((label, account_nr, has_children))
        labels = [label for label, _, _ in options]
        if current_parent is not None:
            labels.insert(0, "⬅️  Go back")
        selected = cast(str | None, beaupy.select(labels, cursor_style="fg:#00ff00 bold", cursor="➤ "))
        if selected is None:
            print("No account selected. Exiting.")
            return None
        if current_parent is not None and selected == "⬅️  Go back":
            # Go up one level
            current_parent = parent_map.get(current_parent)
            path.pop()
            continue
        idx = labels.index(selected)
        if current_parent is not None:  
            idx -= 1  # Adjust for 'Go back' option
        _label, selected_account_nr, has_children = options[idx]
        if has_children:
            # Go down one level
            path.append(selected_account_nr)
            current_parent = selected_account_nr
            continue
        else:
            # Leaf node selected
            return str(selected_account_nr)


def print_list_accounts(date: str | None = None, raw: bool = False) -> None:
    """
    List Conscribo accounts for a given date.
    """
    print(f"Listing Conscribo accounts for date: {date}")
    ans: ConscriboAccountsResponse = list_conscribo_accounts(date)
    if raw:
        print(json.dumps(ans, indent=2))
        return
    
    accounts = ans["accounts"]
    # These are two sample elements from accounts:
    # {
    #   "accountNr": "8001",
    #   "accountName": "Ledencontributie",
    #   "type": "result",
    #   "usage": "generic",
    #   "usedForCredit": true,
    #   "usedForDebit": true,
    #   "parent": "8000"
    # },
    # {
    #   "accountNr": "8000",
    #   "accountName": "Inkomsten",
    #   "type": "result",
    #   "usage": "generic",
    #   "usedForCredit": false,
    #   "usedForDebit": false
    # },
    #
    # We want to print a tree of them. For these two elements, we would print:
    #  8000: Inkomsten
    #     └── 8001: Ledencontributie
    #
    # ...
    # ├── 8000: Inkomsten
    # │    ├── 8001: Ledencontributie
    # │    ├── 8002: Reünistencontributie
    # │    ├── 8010: Subsidies
    # │    │    ├── 8013: Universiteit Utrecht
    # │    │    └── 8014: Hogeschool Utrecht
    # │    ├── 8020: Sponsoring
    # ...  ...
    # 
    print_account_tree(accounts)
    print("\n\n")