from django.shortcuts import render

from dashboard.services import SlurmError

from .services import get_accounts_page_data


def account_list(request):
    """
    Main Slurm Accounts page.
    """

    account_filter = request.GET.get(
        "account",
        "*",
    ).strip() or "*"

    user_filter = request.GET.get(
        "user",
        "*",
    ).strip() or "*"

    cluster_filter = request.GET.get(
        "cluster",
        "*",
    ).strip() or "*"

    partition_filter = request.GET.get(
        "partition",
        "*",
    ).strip() or "*"

    error = None

    try:

        data = get_accounts_page_data(
            account_filter=account_filter,
            user_filter=user_filter,
            cluster_filter=cluster_filter,
            partition_filter=partition_filter,
        )

    except SlurmError as exc:

        data = {
            "accounts": [],
            "account_tree": [],
            "users": [],
            "associations": [],
            "qos": [],
            "summary": {
                "accounts": 0,
                "users": 0,
                "associations": 0,
            },
        }

        error = str(exc)

    context = {
        **data,

        "error": error,

        "filters": {
            "account": account_filter,
            "user": user_filter,
            "cluster": cluster_filter,
            "partition": partition_filter,
        },
    }

    return render(
        request,
        "accounts/list.html",
        context,
    )

# Create your views here.
