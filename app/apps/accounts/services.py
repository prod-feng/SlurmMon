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

    Parent/child relationships are represented by the 'parent'
    field.

    Slurm supports hierarchical accounts with arbitrary depth.
    """

    output = _run_sacctmgr([
        "show",
        "account",
        "format=Account,Description,Organization,ParentName",
    ])

    accounts = []

    for parts in _split_rows(output, 4):

        name = parts[0].strip()

        if not name:
            continue

        if not _matches(name, account_filter):
            continue

        accounts.append({
            "name": name,
            "description": parts[1].strip(),
            "organization": parts[2].strip(),
            "parent": parts[3].strip(),
            "children": [],
            "users": [],
        })

    # Build parent -> children relationships.
    account_map = {
        account["name"]: account
        for account in accounts
    }

    for account in accounts:

        parent = account["parent"]

        if parent and parent in account_map:
            account_map[parent]["children"].append(account)

    return accounts


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
        "format=Cluster,Account,User,Partition,Fairshare,DefaultQOS,QOS",
    ])

    associations = []

    for parts in _split_rows(output, 7):

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
            "default_qos": parts[5].strip(),
            "qos": parts[6].strip(),
        })

    return associations


def build_account_tree(accounts):
    """
    Convert a flat account list into a hierarchical tree.

    The returned structure contains only root accounts.
    Children are nested under each account.
    """

    account_map = {
        account["name"]: account
        for account in accounts
    }

    roots = []

    for account in accounts:

        parent = account["parent"]

        if parent and parent in account_map:
            continue

        roots.append(account)

    return roots


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

    tree = build_account_tree(accounts)

    return {
        "accounts": accounts,
        "account_tree": tree,
        "users": users,
        "associations": associations,
        "summary": {
            "accounts": len(accounts),
            "users": len(users),
            "associations": len(associations),
        },
    }

