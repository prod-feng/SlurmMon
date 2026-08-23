from django.shortcuts import render

from .services import (
    SlurmError,
    get_cluster_summary,
)


def dashboard(request):
    """
    Display the Slurm cluster summary dashboard.
    """

    error = None

    # Default values so the page can still render if Slurm
    # temporarily becomes unavailable.
    summary = {
        "nodes": {
            "total": 0,
            "idle": 0,
            "allocated": 0,
            "down": 0,
        },

        "cpus": {
            "total": 0,
        },

        "gpus": {
            "total": 0,
            "allocated": 0,
            "available": 0,
            "by_type": {},
        },

        "jobs": {
            "total": 0,
            "running": 0,
            "pending": 0,
        },

        "partitions": {
            "total": 0,
        },
    }

    try:
        summary = get_cluster_summary()

    except SlurmError as exc:
        error = str(exc)

    context = {
        "error": error,

        "node_stats": summary["nodes"],

        "cpu_stats": summary["cpus"],

        "gpu_stats": summary["gpus"],

        "job_stats": summary["jobs"],

        "partition_stats": summary["partitions"],
    }

    return render(
        request,
        "dashboard/index.html",
        context,
    )

