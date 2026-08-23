from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import JobService


@login_required
def job_list(request):
    try:
        jobs = JobService().list_jobs()
        error = None
    except Exception as exc:
        jobs = []
        error = str(exc)

    return render(
        request,
        "jobs/list.html",
        {
            "jobs": jobs,
            "error": error,
        },
    )

