import json
import beaupy

from sib_tools.conscribo.finance import (
    list_conscribo_accounts,
)

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

def build_account_options(accounts, parent_id=None, prefix=""):
    options = []
    children = [a for a in accounts if a.get("parent") == parent_id]
    total = len(children)
    for idx, account in enumerate(children):
        is_last = idx == (total - 1)
        branch = "└── " if is_last else "├── "
        label = prefix + branch + f"{account['accountNr']}: {account['accountName']}"
        next_prefix = prefix + ("     " if is_last else "│    ")
        options.append((account['accountNr'], label, next_prefix))
        options += build_account_options(accounts, account["accountNr"], next_prefix)
    return options

def print_account_tree(accounts: list[dict], parent_id: str = None, prefix: str = ""):
    """
    Print a tree structure of accounts.
    """
    options = build_account_options(accounts, parent_id, prefix)
    for account_id, label, _ in options:
        print(label)
    if not options:
        print(prefix + "No accounts found.")

def show_choose_account_tall(date : str|None) -> str:
    # This version can cause problems because of being too tall for the terminal.

    # Fetch accounts for selection
    # ans = list_conscribo_accounts(getattr(args, 'date', None))
    ans = list_conscribo_accounts(date=date)
    accounts = ans["accounts"]
    # Build a flat list of account options for selector

    options = build_account_options(accounts)
    labels = [label for _, label, _ in options]
    selected = beaupy.select(labels, cursor_style="fg:#00ff00 bold", cursor="➤ ")
    if selected is not None:
        idx = labels.index(selected)
        account_id = options[idx][0]
        return account_id

    print("No account selected. Exiting.")
    return None


def show_choose_account(date: str | None) -> str:
    """
    Interactive account selector with navigation through account levels.
    """
    ans = list_conscribo_accounts(date=date)
    accounts = ans["accounts"]

    # Build a lookup for children and parents
    from collections import defaultdict
    children_map = defaultdict(list)
    parent_map = {}
    for acc in accounts:
        parent = acc.get("parent")
        children_map[parent].append(acc)
        parent_map[acc["accountNr"]] = parent

    current_parent = None
    path = []
    while True:
        current_accounts = children_map.get(current_parent, [])
        options = []
        for acc in current_accounts:
            # Mark if this account has children
            has_children = len(children_map.get(acc["accountNr"], [])) > 0
            label = f"{acc['accountNr']}: {acc['accountName']}"
            if has_children:
                label += " [>]"
            options.append((label, acc["accountNr"], has_children))
        labels = [label for label, _, _ in options]
        if current_parent is not None:
            labels.insert(0, "⬅️  Go back")
        selected = beaupy.select(labels, cursor_style="fg:#00ff00 bold", cursor="➤ ")
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
        acc = options[idx]
        if acc[2]:  # has_children
            # Go down one level
            path.append(acc[1])
            current_parent = acc[1]
            continue
        else:
            # Leaf node selected
            return acc[1]


def print_list_accounts(date: str | None = None, raw: bool = False):
    """
    List Conscribo accounts for a given date.
    """
    print(f"Listing Conscribo accounts for date: {date}")
    ans : list[dict] = list_conscribo_accounts(date)
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