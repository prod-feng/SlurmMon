from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import ClusterService


@login_required
def dashboard(request):
    try:
        status = ClusterService().status()
        error = None
    except Exception as exc:
        status = []
        error = str(exc)

    return render(
        request,
        "dashboard.html",
        {
            "status": status,
            "error": error,
        },
    )

