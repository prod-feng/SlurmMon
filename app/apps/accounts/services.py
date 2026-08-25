import fnmatch

from dashboard.services import SlurmError, run_slurm


def _run_sacctmgr(args):
    """
    Execute sacctmgr through the existing Slurm command wrapper.

    We deliberately use -P so the output is pipe-delimited without
    trailing padding, making it much easier to parse reliably.
    """

    return run_slurm([
        "sacctmgr",
        "-n",
        "-P",
        *args,
    ])


def _split_rows(output, expected_fields):
    """
    Parse sacctmgr -P output.

    sacctmgr can occasionally return blank lines.
    """

    rows = []

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        parts = line.split("|")

        # Ignore malformed rows.
        if len(parts) < expected_fields:
            continue

        rows.append(parts)

    return rows


def _matches(value, pattern):
    """
    Case-insensitive shell-style wildcard matching.

    Supported:
        *
        ?
    """

    if not pattern or pattern == "*":
        return True

    return fnmatch.fnmatchcase(
        value.lower(),
        pattern.lower(),
    )


def get_accounts(account_filter="*"):
    """
    Return Slurm accounts and their hierarchy.

    Supports arbitrary hierarchy depth.

    When an account filter is supplied, matching accounts are
    returned together with all of their ancestors so the complete
    hierarchy remains visible.
    """

    output = _run_sacctmgr([
        "show",
        "account",
        "format=Account,Description,Organization,ParentName",
    ])

    all_accounts = []

    for parts in _split_rows(output, 4):

        name = parts[0].strip()

        if not name:
            continue

        all_accounts.append({
            "name": name,
            "description": parts[1].strip(),
            "organization": parts[2].strip(),
            "parent": parts[3].strip(),
            "children": [],
            "users": [],
        })

    # Lookup table containing the complete hierarchy.
    account_map = {
        account["name"]: account
        for account in all_accounts
    }

    # Find accounts that directly match the filter.
    matching_names = {
        account["name"]
        for account in all_accounts
        if _matches(account["name"], account_filter)
    }

    # Include all ancestors of matching accounts.
    included_names = set(matching_names)

    for account_name in list(matching_names):

        current = account_map.get(account_name)

        while current:

            parent_name = current["parent"]

            if not parent_name:
                break

            parent = account_map.get(parent_name)

            if parent is None:
                break

            included_names.add(parent_name)
            current = parent

    # Keep only the accounts needed for the filtered hierarchy.
    accounts = [
        account
        for account in all_accounts
        if account["name"] in included_names
    ]

    # Reset children and rebuild the hierarchy.
    account_map = {
        account["name"]: account
        for account in accounts
    }

    for account in accounts:
        account["children"] = []

    for account in accounts:

        parent_name = account["parent"]

        if not parent_name:
            continue

        parent = account_map.get(parent_name)

        if parent is not None:
            parent["children"].append(account)

    return accounts

def get_account_tree(account_filter="*"):
    """
    Build the Slurm account hierarchy from:

        sacctmgr list associations tree

    Supports arbitrary hierarchy depth.

    Account rows define the hierarchy.
    User rows are attached to their account.
    """

    output = run_slurm([
        "sacctmgr",
        "-n",
        "-P",
        "list",
        "associations",
        "tree",
        "format=Account,User,ParentName",
    ])

    accounts = {}
    users_by_account = {}

    for parts in _split_rows(output, 3):

        account_name = parts[0].strip()
        user_name = parts[1].strip()
        parent_name = parts[2].strip()

        if not account_name:
            continue

        # User association row.
        if user_name:

            users_by_account.setdefault(
                account_name,
                [],
            )

            if user_name not in users_by_account[account_name]:
                users_by_account[account_name].append(
                    user_name
                )

            continue

        # Account row.
        if account_name not in accounts:

            accounts[account_name] = {
                "name": account_name,
                "description": "",
                "organization": "",
                "parent": parent_name,
                "children": [],
                "users": [],
            }

        else:

            # The account may have appeared previously
            # through a user association.
            if parent_name:
                accounts[account_name]["parent"] = parent_name

    # Attach users.
    for account_name, users in users_by_account.items():

        account = accounts.get(account_name)

        if account is not None:
            account["users"] = users

# --------------------------------------------------
# Remove Slurm's structural "root" account.
# --------------------------------------------------

    accounts.pop("root", None)

    # Build parent -> child relationships.
    for account in accounts.values():

        account["children"] = []

    for account in accounts.values():

        parent_name = account["parent"]

        if not parent_name or parent_name.lower() == "root":
            continue

        parent = accounts.get(parent_name)

        if parent is not None:
            parent["children"].append(account)

    # --------------------------------------------------
    # Filtering
    # --------------------------------------------------

    if account_filter and account_filter != "*":

        matching = set()

        for account in accounts.values():

            if _matches(
                account["name"],
                account_filter,
            ):
                matching.add(account["name"])

        # Include all ancestors.
        for account_name in list(matching):

            current = accounts.get(account_name)

            while current:

                parent_name = current["parent"]

                if (
                    not parent_name
                    or parent_name.lower() == "root"
                ):
                    break

                parent = accounts.get(parent_name)

                if parent is None:
                    break

                matching.add(parent_name)
                current = parent

        accounts = {
            name: account
            for name, account in accounts.items()
            if name in matching
        }

        # Rebuild children after filtering.
        for account in accounts.values():
            account["children"] = []

        for account in accounts.values():

            parent_name = account["parent"]

            if not parent_name:
                continue

            parent = accounts.get(parent_name)

            if parent is not None:
                parent["children"].append(account)

    # --------------------------------------------------
    # Return root accounts.
    # --------------------------------------------------

    roots = []

    for account in accounts.values():

        parent_name = account["parent"]

        if (
            not parent_name
            or parent_name.lower() == "root"
            or parent_name not in accounts
        ):
            roots.append(account)

    return roots


def get_users(user_filter="*"):
    """
    Return unique Slurm users.

    A user can have multiple associations, so users are deduplicated.
    """

    output = _run_sacctmgr([
        "show",
        "user",
        "format=User,DefaultAccount,DefaultWCKey,AdminLevel",
    ])

    users = []

    for parts in _split_rows(output, 4):

        name = parts[0].strip()

        if not name:
            continue

        if not _matches(name, user_filter):
            continue

        users.append({
            "name": name,
            "default_account": parts[1].strip(),
            "default_wckey": parts[2].strip(),
            "admin_level": parts[3].strip(),
        })

    return users


def get_associations(
    account_filter="*",
    user_filter="*",
    cluster_filter="*",
    partition_filter="*",
):
    """
    Return Slurm associations.

    A Slurm association consists of:

        cluster
        account
        user
        optional partition

    We retrieve the accounting database information and apply
    wildcard filters to the individual fields.
    """

    output = _run_sacctmgr([
        "show",
        "association",
        "format="
        "Cluster,"
        "Account,"
        "User,"
        "Partition,"
        "Fairshare,"
        "Priority,"
        "DefaultQOS,"
        "QOS,"
        "GrpTRES,"
        "GrpTRESMins,"
        "MaxTRES,"
        "MaxTRESMins,"
        "MaxJobs,"
        "MaxSubmitJobs,"
        "MaxWall",
    ])

    associations = []

    for parts in _split_rows(output, 15):

        cluster = parts[0].strip()
        account = parts[1].strip()
        user = parts[2].strip()
        partition = parts[3].strip()

        if not _matches(account, account_filter):
            continue

        if not _matches(user, user_filter):
            continue

        if not _matches(cluster, cluster_filter):
            continue

        if not _matches(partition, partition_filter):
            continue

        associations.append({
            "cluster": cluster,
            "account": account,
            "user": user,
            "partition": partition or "—",

            "fairshare": parts[4].strip(),
            "priority": parts[5].strip(),

            "default_qos": parts[6].strip(),
            "qos": parts[7].strip(),

            "grp_tres": parts[8].strip(),
            "grp_tres_mins": parts[9].strip(),

            "max_tres": parts[10].strip(),
            "max_tres_mins": parts[11].strip(),

            "max_jobs": parts[12].strip(),
            "max_submit_jobs": parts[13].strip(),

            "max_wall": parts[14].strip(),
        })

    return associations



def attach_users_to_accounts(accounts, associations):
    """
    Add users to the account objects based on associations.
    """

    account_map = {
        account["name"]: account
        for account in accounts
    }

    for association in associations:

        account_name = association["account"]
        user_name = association["user"]

        if not user_name:
            continue

        account = account_map.get(account_name)

        if account is None:
            continue

        if user_name not in account["users"]:
            account["users"].append(user_name)


def get_summary():
    """
    Summary numbers for the Accounts page.
    """

    accounts = get_accounts()
    users = get_users()
    associations = get_associations()

    return {
        "accounts": len(accounts),
        "users": len(users),
        "associations": len(associations),
    }


def get_accounts_page_data(
    account_filter="*",
    user_filter="*",
    cluster_filter="*",
    partition_filter="*",
):
    """
    Retrieve everything needed by the Accounts page.
    """

    qos = get_qos()

    accounts = get_accounts(account_filter)

    associations = get_associations(
        account_filter=account_filter,
        user_filter=user_filter,
        cluster_filter=cluster_filter,
        partition_filter=partition_filter,
    )

    users = get_users(user_filter)

    # Add associated users to accounts.
    attach_users_to_accounts(
        accounts,
        associations,
    )

    account_tree = get_account_tree(account_filter)
    assign_tree_classes(account_tree)

    print("\n=== ACCOUNT TREE COLORS ===")


    def debug_tree(nodes, indent=0):
        for account in nodes:
            print(
             " " * indent,
             account["name"],
             "=>",
             account.get("zebra_class"),
             "depth=",
             account.get("tree_depth"),
            )

            debug_tree(
             account.get("children") or [],
             indent + 4,
            )


    debug_tree(account_tree)

    print("===========================\n")


    return {
        "accounts": accounts,
        "account_tree": account_tree,
        "users": users,
        "associations": associations,
        "qos": qos,
        "summary": {
            "accounts": len(accounts),
            "users": len(users),
            "associations": len(associations),
        },
    }

def get_qos():
    """
    Return configured Slurm Quality of Service entries.
    """

    output = _run_sacctmgr([
        "show",
        "qos",
        "format=Name,Priority,GraceTime,Preempt,PreemptMode,"
        "Flags,MaxTRES,MaxTRESMins,MaxJobsPU,MaxSubmitJobsPU,"
        "MaxWall,GrpTRES,GrpTRESMins",
    ])

    qos_list = []

    for parts in _split_rows(output, 13):

        name = parts[0].strip()

        if not name:
            continue

        qos_list.append({
            "name": name,
            "priority": parts[1].strip(),
            "grace_time": parts[2].strip(),
            "preempt": parts[3].strip(),
            "preempt_mode": parts[4].strip(),
            "flags": parts[5].strip(),
            "max_tres": parts[6].strip(),
            "max_tres_mins": parts[7].strip(),
            "max_jobs": parts[8].strip(),
            "max_submit_jobs": parts[9].strip(),
            "max_wall": parts[10].strip(),
            "grp_tres": parts[11].strip(),
            "grp_tres_mins": parts[12].strip(),
        })

    return qos_list

def assign_tree_classes(accounts):
    """
    Assign zebra classes to the account tree.

    Level 0:
        Departments alternate colors.

    Level 1:
        PIs alternate colors.

    Level 2+:
        All descendants inherit their PI's color.

    Users:
        Use the same class as their account.
    """

    def walk(nodes, depth=0, inherited_class=None):

        for index, account in enumerate(nodes):

            if depth == 0:
                # Department color
                if index % 2 == 0:
                    zebra_class = "tree-level-0-odd"
                else:
                    zebra_class = "tree-level-0-even"

            elif depth == 1:
                # PI color
                if index % 2 == 0:
                    zebra_class = "tree-level-1-odd"
                else:
                    zebra_class = "tree-level-1-even"

            else:
                # PN / course / deeper accounts:
                # inherit the PI's color.
                zebra_class = inherited_class

            account["tree_depth"] = depth
            account["zebra_class"] = zebra_class

            # Users should use the same color as this account.
            account["users_zebra_class"] = zebra_class

            walk(
                account.get("children", []),
                depth + 1,
                zebra_class,
            )

    walk(accounts)



def assign_tree_styles(accounts, level=0):
    """
    Recursively assign zebra-striping classes to an account tree.

    Parameters
    ----------
    accounts:
        List of account dictionaries at the current hierarchy level.

    level:
        Current hierarchy depth.

        0 = top-level account
        1 = child
        2 = grandchild
        3 = great-grandchild
        etc.

    Example input:

        [
            {
                "name": "dept_A",
                "children": [
                    {
                        "name": "pi_1",
                        "children": []
                    },
                    {
                        "name": "pi_2",
                        "children": []
                    }
                ]
            },
            {
                "name": "dept_B",
                "children": []
            }
        ]

    The function modifies each account dictionary in-place.
    """

    for index, account in enumerate(accounts):

        # -------------------------------------------------
        # Determine whether this account is odd or even
        # among its siblings.
        #
        # index 0 -> odd
        # index 1 -> even
        # index 2 -> odd
        # index 3 -> even
        # -------------------------------------------------

        if index % 2 == 0:
            parity = "odd"
        else:
            parity = "even"


        # -------------------------------------------------
        # Save the hierarchy level.
        #
        # This can be useful later in the template/CSS.
        # -------------------------------------------------

        account["tree_level"] = level


        # -------------------------------------------------
        # Build the CSS class.
        #
        # Level 0:
        #
        #   tree-row-odd
        #   tree-row-even
        #
        # Level 1:
        #
        #   tree-row-level-1-odd
        #   tree-row-level-1-even
        #
        # Level 2:
        #
        #   tree-row-level-2-odd
        #   tree-row-level-2-even
        #
        # etc.
        # -------------------------------------------------

        if level == 0:

            account["zebra_class"] = (
                f"tree-row-{parity}"
            )

        else:

            account["zebra_class"] = (
                f"tree-row-level-{level}-{parity}"
            )


        # -------------------------------------------------
        # Get this account's children.
        #
        # "or []" protects us if children is missing or None.
        # -------------------------------------------------

        children = account.get("children") or []


        # -------------------------------------------------
        # Recursively process the children.
        #
        # IMPORTANT:
        #
        # We pass level + 1.
        #
        # The enumerate() inside the next invocation starts
        # at zero again, so each parent's children get their
        # own independent odd/even sequence.
        # -------------------------------------------------

        if children:

            assign_tree_styles(
                children,
                level=level + 1,
            )

