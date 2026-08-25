from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import JobService


@login_required
def job_list(request):

    sort = request.GET.get(
        "sort",
        "id",
    )

    direction = request.GET.get(
        "direction",
        "asc",
    )

    # Only allow the two expected directions.
    if direction not in ("asc", "desc"):
        direction = "asc"

    try:

        jobs = JobService().list_jobs(
            sort=sort,
            direction=direction,
        )

        error = None

    except Exception as exc:

        jobs = []
        error = str(exc)

    context = {
        "jobs": jobs,
        "error": error,
        "sort": sort,
        "direction": direction,
    }

    return render(
        request,
        "jobs/list.html",
        context,
    )

@login_required
def job_detail(request, job_id):

    try:
        job = JobService().get_job(job_id)
        error = None

    except Exception as exc:
        job = None
        error = str(exc)

    context = {
        "job": job,
        "error": error,
    }

    return render(
        request,
        "jobs/detail.html",
        context,
    )

