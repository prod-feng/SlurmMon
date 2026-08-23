from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import PartitionService


@login_required
def partition_list(request):
    try:
        partitions = PartitionService().list_partitions()
        error = None
    except Exception as exc:
        partitions = []
        error = str(exc)

    return render(
        request,
        "partitions/list.html",
        {
            "partitions": partitions,
            "error": error,
        },
    )

