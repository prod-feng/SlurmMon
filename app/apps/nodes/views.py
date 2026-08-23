from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .services import NodeService


from django.shortcuts import render

from dashboard.services import SlurmError, run_slurm

@login_required
def node_list(request):

    error = None
    nodes_by_name = {}

    try:

        output = run_slurm([
            "sinfo",
            "-a",
            "-N",
            "-h",
            "-o",
            "%N|%T|%c|%m|%P",
        ])

        for line in output.splitlines():

            line = line.strip()

            if not line:
                continue

            parts = line.split("|")

            if len(parts) != 5:
                continue

            name = parts[0].strip()
            state = parts[1].strip()
            cpus = parts[2].strip()
            memory = parts[3].strip()
            partition = parts[4].strip().rstrip("*")

            if not name:
                continue

            if name not in nodes_by_name:

                nodes_by_name[name] = {
                    "name": name,
                    "state": state,
                    "cpus": cpus,
                    "memory_mb": memory,
                    "partitions": [],
                }

            node = nodes_by_name[name]

            # Add this partition only once.
            if (
                partition
                and partition not in node["partitions"]
            ):
                node["partitions"].append(partition)


        nodes = list(nodes_by_name.values())

        # Convert the partition list into display text.
        for node in nodes:

            node["partition"] = ", ".join(
                node["partitions"]
            )


    except SlurmError as exc:

        nodes = []
        error = str(exc)


    context = {
        "nodes": nodes,
        "error": error,
    }

    return render(
        request,
        "nodes/list.html",
        context,
    )


@login_required
def drain_node(request, node):
    if request.method != "POST":
        return redirect("nodes:list")

    if not request.user.is_staff:
        messages.error(request, "Administrator privileges required.")
        return redirect("nodes:list")

    reason = request.POST.get("reason", "")

    try:
        NodeService().drain(node, reason)
        messages.success(
            request,
            f"{node} has been placed in DRAIN state.",
        )
    except Exception as exc:
        messages.error(request, str(exc))

    return redirect("nodes:list")


@login_required
def resume_node(request, node):
    if request.method != "POST":
        return redirect("nodes:list")

    if not request.user.is_staff:
        messages.error(request, "Administrator privileges required.")
        return redirect("nodes:list")

    try:
        NodeService().resume(node)
        messages.success(
            request,
            f"{node} has been resumed.",
        )
    except Exception as exc:
        messages.error(request, str(exc))

    return redirect("nodes:list")

