import os
import subprocess

from django.conf import settings


class SlurmError(Exception):
    """Raised when a Slurm command cannot be executed successfully."""


def run_slurm(command):
    """
    Execute a Slurm command using the configured Slurm installation.

    Example:

        run_slurm(["sinfo", "-a", "-h", "-o", "%N|%T|%c"])

    The first command argument can be either:
        "sinfo"
        "squeue"

    or an absolute path.
    """

    if not command:
        raise SlurmError("No Slurm command specified.")

    executable = command[0]

    # Use SLURM_BIN for commands such as "sinfo" and "squeue".
    if not os.path.isabs(executable):
        executable = os.path.join(
            settings.SLURM_BIN,
            executable,
        )

    full_command = [
        executable,
        *command[1:],
    ]

    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=settings.SLURM_TIMEOUT,
            check=False,
        )

    except subprocess.TimeoutExpired as exc:
        raise SlurmError(
            f"Slurm command timed out after "
            f"{settings.SLURM_TIMEOUT} seconds: "
            f"{' '.join(full_command)}"
        ) from exc

    except OSError as exc:
        raise SlurmError(
            f"Unable to execute Slurm command "
            f"{' '.join(full_command)}: {exc}"
        ) from exc

    if result.returncode != 0:

        error = result.stderr.strip()

        if not error:
            error = (
                f"Slurm command exited with "
                f"status {result.returncode}"
            )

        raise SlurmError(
            f"{' '.join(full_command)}: {error}"
        )

    return result.stdout


def get_nodes_summary():
    """
    Get a unique list of physical cluster nodes.

    Important:
    A node may belong to several Slurm partitions, so sinfo can
    return the same node multiple times.

    Example:

        cpu021 | idle | 64
        cpu021 | idle | 64
        cpu021 | idle | 64

    represents ONE physical node with 64 CPUs.

    Returns:

        {
            "total": 15,
            "idle": 15,
            "allocated": 0,
            "down": 0,
            "cpus": 960,
        }
    """

    output = run_slurm([
        "sinfo",
        "-a",
        "-N",
        "-h",
        "-o",
        "%N|%T|%c",
    ])

    nodes = {}

    for line in output.splitlines():

        line = line.strip()

        if not line:
            continue

        parts = line.split("|")

        if len(parts) != 3:
            continue

        node_name = parts[0].strip()
        state = parts[1].strip().upper()

        try:
            cpus = int(parts[2].strip())
        except ValueError:
            cpus = 0

        if not node_name:
            continue

        # -------------------------------------------------
        # Deduplicate nodes.
        # -------------------------------------------------

        if node_name not in nodes:

            nodes[node_name] = {
                "state": state,
                "cpus": cpus,
            }

            continue

        # -------------------------------------------------
        # Same node appeared in another partition.
        #
        # Keep the CPU count from the first occurrence.
        # Do not add it again.
        # -------------------------------------------------

        existing_state = nodes[node_name]["state"]

        # Prefer a non-IDLE state if different partitions
        # report different states for the same physical node.
        if existing_state.startswith("IDLE"):

            if not state.startswith("IDLE"):
                nodes[node_name]["state"] = state


    total = len(nodes)

    idle = 0
    allocated = 0
    down = 0
    cpus = 0


    for node in nodes.values():

        state = node["state"]

        cpus += node["cpus"]

        if state.startswith("IDLE"):

            idle += 1

        elif state.startswith("DOWN"):

            down += 1

        elif (
            state.startswith("ALLOC")
            or state.startswith("MIX")
            or state.startswith("COMP")
        ):

            allocated += 1


        elif (
            state.startswith("DRAIN")
            or state.startswith("FAIL")
            or state.startswith("INVAL")
        ):

            down += 1


    return {
        "total": total,
        "idle": idle,
        "allocated": allocated,
        "down": down,
        "cpus": cpus,
    }


def get_jobs_summary():
    """
    Get the current Slurm job summary.

    Returns:

        {
            "total": 11,
            "running": 10,
            "pending": 1,
        }
    """

    output = run_slurm([
        "squeue",
        "-a",
        "-h",
        "-o",
        "%T",
    ])

    total = 0
    running = 0
    pending = 0

    for line in output.splitlines():

        state = line.strip().upper()

        if not state:
            continue

        total += 1

        if state == "RUNNING":

            running += 1

        elif state == "PENDING":

            pending += 1


    return {
        "total": total,
        "running": running,
        "pending": pending,
    }


def get_partitions_summary():
    """
    Get the number of unique Slurm partitions.

    sinfo can return a partition multiple times because it can
    have multiple nodes/states.

    Returns:

        {
            "total": 3,
        }
    """

    output = run_slurm([
        "sinfo",
        "-a",
        "-h",
        "-o",
        "%P",
    ])

    partitions = set()

    for line in output.splitlines():

        partition = line.strip()

        if not partition:
            continue

        # Slurm marks the default partition with '*'.
        partition = partition.rstrip("*")

        if partition:
            partitions.add(partition)


    return {
        "total": len(partitions),
    }


def get_cluster_summary():
    """
    Get all information required by the dashboard.

    Returns:

        {
            "nodes": {
                "total": ...,
                "idle": ...,
                "allocated": ...,
                "down": ...,
            },

            "cpus": {
                "total": ...,
            },

            "jobs": {
                "total": ...,
                "running": ...,
                "pending": ...,
            },

            "partitions": {
                "total": ...,
            },
        }
    """

    node_summary = get_nodes_summary()

    job_summary = get_jobs_summary()

    partition_summary = get_partitions_summary()


    return {

        "nodes": {
            "total": node_summary["total"],
            "idle": node_summary["idle"],
            "allocated": node_summary["allocated"],
            "down": node_summary["down"],
        },

        "cpus": {
            "total": node_summary["cpus"],
        },

        "jobs": {
            "total": job_summary["total"],
            "running": job_summary["running"],
            "pending": job_summary["pending"],
        },

        "partitions": {
            "total": partition_summary["total"],
        },

    }

