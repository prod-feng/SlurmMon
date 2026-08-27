import os
import subprocess

from django.conf import settings


class SlurmError(Exception):
    """Raised when a Slurm command cannot be executed successfully."""


def run_slurm(command):
    """
    Execute a Slurm command using the configured Slurm installation.

    The first command argument can be:
        "sinfo"
        "squeue"
        "scontrol"

    or an absolute path.
    """

    if not command:
        raise SlurmError("No Slurm command specified.")

    executable = command[0]

    # Use SLURM_BIN for commands such as sinfo, squeue and scontrol.
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


def parse_gres(gres):
    """
    Parse Slurm GPU GRES information.
    Returns:

        {
            "type": "a100",
            "total": 8,
        }

    or:

        {
            "type": None,
            "total": 0,
        }
    """

    if not gres:
        return {
            "type": None,
            "total": 0,
        }

    gres = gres.strip()

    if gres.lower() in ("(null)", "n/a", "none"):
        return {
            "type": None,
            "total": 0,
        }

    # A node may theoretically have multiple GRES values.
    # We are interested in GPU GRES here.
    gpu_entries = [
        entry
        for entry in gres.split(",")
        if entry.startswith("gpu:")
    ]

    if not gpu_entries:
        return {
            "type": None,
            "total": 0,
        }

    # Current cluster format:
    #
    #     gpu:a100:8
    #
    # or:
    #
    #     gpu:6000:4
    #
    first = gpu_entries[0]

    parts = first.split(":")

    if len(parts) < 3:
        return {
            "type": None,
            "total": 0,
        }

    gpu_type = parts[1]

    try:
        # Slurm may append socket information:
        #
        # gpu:a100:4(S:0-1)
        #
        # We only want the numeric GPU count.
        total = int(parts[2].split("(", 1)[0])        
#        total = int(parts[2])
    except ValueError:
        total = 0

    return {
        "type": gpu_type,
        "total": total,
    }


def parse_allocated_gpus(alloc_tres):
    """
    Extract allocated GPU count from Slurm AllocTRES.

    Example:

        cpu=32,mem=200G,gres/gpu=5,gres/gpu:a100=5

    returns:

        5
    """

    if not alloc_tres:
        return 0

    for tres in alloc_tres.split(","):

        tres = tres.strip()

        if tres.startswith("gres/gpu="):

            try:
                return int(
                    tres.split("=", 1)[1]
                )
            except ValueError:
                return 0

    return 0


def get_node_gpu_info():
    """
    Get GPU information for every physical node.

    scontrol returns one record per physical node, so unlike
    sinfo -N there is no duplication caused by partitions.

    Returns:

        {
            "gpu007": {
                "type": "a100",
                "total": 8,
                "allocated": 5,
                "available": 3,
            },

            "gpu011": {
                "type": "6000",
                "total": 4,
                "allocated": 0,
                "available": 4,
            },
        }
    """

    output = run_slurm([
        "scontrol",
        "show",
        "node",
        "-o",
    ])

    nodes = {}

    for line in output.splitlines():

        line = line.strip()

        if not line:
            continue

        fields = {}

        # scontrol -o produces:
        #
        # NodeName=gpu007 CPUAlloc=32 ... Gres=gpu:a100:8 ...
        #
        for item in line.split():

            if "=" not in item:
                continue

            key, value = item.split("=", 1)

            fields[key] = value

        node_name = fields.get("NodeName")

        if not node_name:
            continue

        gres = fields.get("Gres", "")

        gpu = parse_gres(gres)

        total = gpu["total"]

        allocated = parse_allocated_gpus(
            fields.get("AllocTRES", "")
        )

        # Never allow an impossible value.
        allocated = min(
            allocated,
            total,
        )

        available = max(
            total - allocated,
            0,
        )

        nodes[node_name] = {
            "type": gpu["type"],
            "total": total,
            "allocated": allocated,
            "available": available,
        }

    return nodes


def get_nodes_summary():
    """
    Get a unique list of physical cluster nodes.

    A node may belong to several Slurm partitions, so sinfo can
    return the same physical node multiple times.

    CPUs and GPUs are therefore counted only once per node.

    Returns:

        {
            "total": 15,
            "idle": 15,
            "allocated": 0,
            "down": 0,
            "cpus": 960,
            "gpus": {
                "total": 12,
                "by_type": {
                    "a100": 8,
                    "6000": 4,
                },
            },
        }
    """

    output = run_slurm([
        "sinfo",
        "-a",
        "-N",
        "-h",
        "-o",
        "%N|%T|%c|%G",
    ])

    nodes = {}

    for line in output.splitlines():

        line = line.strip()

        if not line:
            continue

        parts = line.split("|")

        if len(parts) != 4:
            continue

        node_name = parts[0].strip()
        state = parts[1].strip().upper()

        try:
            cpus = int(parts[2].strip())
        except ValueError:
            cpus = 0

        gres = parts[3].strip()

        if not node_name:
            continue

        # -------------------------------------------------
        # IMPORTANT:
        #
        # sinfo returns one row per node/partition.
        #
        # Example:
        #
        # gpu007|mixed|256|gpu:a100:8
        # gpu007|mixed|256|gpu:a100:8
        # gpu007|mixed|256|gpu:a100:8
        #
        # These are ONE physical node.
        # -------------------------------------------------

        if node_name not in nodes:

            gpu = parse_gres(gres)

            nodes[node_name] = {
                "state": state,
                "cpus": cpus,
                "gpus": gpu,
            }

            continue

        # -------------------------------------------------
        # Same physical node appeared in another partition.
        #
        # Do NOT add CPUs or GPUs again.
        # -------------------------------------------------

        existing_state = nodes[node_name]["state"]

        # Prefer a non-IDLE state if different partitions
        # report different states for the same node.
        if existing_state.startswith("IDLE"):

            if not state.startswith("IDLE"):
                nodes[node_name]["state"] = state

    total = len(nodes)

    idle = 0
    allocated = 0
    down = 0
    cpus = 0

    gpu_total = 0
    gpu_by_type = {}

    for node in nodes.values():

        state = node["state"]

        cpus += node["cpus"]

        # -----------------------------
        # Node state
        # -----------------------------

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

        # -----------------------------
        # GPUs
        # -----------------------------

        gpu = node["gpus"]

        gpu_total += gpu["total"]

        gpu_type = gpu["type"]

        if gpu_type:

            gpu_by_type[gpu_type] = (
                gpu_by_type.get(gpu_type, 0)
                + gpu["total"]
            )

    return {
        "total": total,
        "idle": idle,
        "allocated": allocated,
        "down": down,
        "cpus": cpus,
        "gpus": {
            "total": gpu_total,
            "by_type": gpu_by_type,
        },
    }


def get_gpu_summary():
    """
    Get the cluster-wide GPU summary.

    Configured GPU totals come from sinfo and are deduplicated
    by physical node.

    Allocated GPUs come from scontrol.

    Returns:

        {
            "total": 12,
            "allocated": 5,
            "available": 7,
            "by_type": {
                "a100": {
                    "total": 8,
                    "allocated": 5,
                    "available": 3,
                },
                "6000": {
                    "total": 4,
                    "allocated": 0,
                    "available": 4,
                },
            },
        }
    """

    # Configured GPUs, deduplicated by node.
    output = run_slurm([
        "sinfo",
        "-a",
        "-N",
        "-h",
        "-o",
        "%N|%G",
    ])

    configured_nodes = {}

    for line in output.splitlines():

        line = line.strip()

        if not line:
            continue

        parts = line.split("|")

        if len(parts) != 2:
            continue

        node_name = parts[0].strip()
        gres = parts[1].strip()

        if not node_name:
            continue

        # -------------------------------------------------
        # One physical node may appear for many partitions.
        # -------------------------------------------------

        if node_name in configured_nodes:
            continue

        configured_nodes[node_name] = parse_gres(gres)

    # Allocated GPUs.
    allocated_nodes = get_node_gpu_info()

    total = 0
    allocated = 0

    by_type = {}

    for node_name, gpu in configured_nodes.items():

        gpu_total = gpu["total"]
        gpu_type = gpu["type"]

        node_allocated = 0

        if node_name in allocated_nodes:
            node_allocated = allocated_nodes[
                node_name
            ]["allocated"]

        node_allocated = min(
            node_allocated,
            gpu_total,
        )

        node_available = max(
            gpu_total - node_allocated,
            0,
        )

        total += gpu_total
        allocated += node_allocated

        if gpu_type:

            if gpu_type not in by_type:

                by_type[gpu_type] = {
                    "total": 0,
                    "allocated": 0,
                    "available": 0,
                }

            by_type[gpu_type]["total"] += gpu_total
            by_type[gpu_type]["allocated"] += node_allocated
            by_type[gpu_type]["available"] += node_available

    available = max(
        total - allocated,
        0,
    )

    return {
        "total": total,
        "allocated": allocated,
        "available": available,
        "by_type": by_type,
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
    """

    node_summary = get_nodes_summary()

    gpu_summary = get_gpu_summary()

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

        "gpus": gpu_summary,

        "jobs": {
            "total": job_summary["total"],
            "running": job_summary["running"],
            "pending": job_summary["pending"],
        },

        "partitions": {
            "total": partition_summary["total"],
        },

    }

