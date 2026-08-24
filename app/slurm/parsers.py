from dataclasses import dataclass


@dataclass
class NodeInfo:
    name: str
    state: str
    cpus: str
    memory: str
    gres: str
    partitions: str


@dataclass
class PartitionInfo:
    name: str
    availability: str
    time_limit: str
    nodes: str
    cpus: str


@dataclass
class JobInfo:
    job_id: str
    user: str
    partition: str
    name: str
    state: str
    elapsed: str
    nodes: str
    cpus: str
    gpus: str
    nodelist: str    
    reason: str


def _split(line: str) -> list[str]:
    return line.rstrip("\n").split("|")


def parse_nodes(output: str) -> list[NodeInfo]:
    nodes = []

    for line in output.splitlines():
        fields = _split(line)

        if len(fields) != 6:
            continue

        nodes.append(
            NodeInfo(
                name=fields[0],
                state=fields[1],
                cpus=fields[2],
                memory=fields[3],
                gres=fields[4],
                partitions=fields[5],
            )
        )

    return nodes


def parse_partitions(output: str) -> list[PartitionInfo]:
    partitions = []

    for line in output.splitlines():
        fields = _split(line)

        if len(fields) != 5:
            continue

        partitions.append(
            PartitionInfo(
                name=fields[0],
                availability=fields[1],
                time_limit=fields[2],
                nodes=fields[3],
                cpus=fields[4],
            )
        )

    return partitions


def parse_jobs(output: str) -> list[JobInfo]:
    jobs = []

    for line in output.splitlines():
        fields = _split(line)

        if len(fields) != 11:
            continue
        gpus = fields[8].strip()

        # Slurm reports N/A for CPU-only jobs.
        if not gpus or gpus.upper() == "N/A":
            gpus = ""

        jobs.append(
            JobInfo(
                job_id=fields[0],
                user=fields[1],
                partition=fields[2],
                name=fields[3],
                state=fields[4],
                elapsed=fields[5],
                nodes=fields[6],
                cpus=fields[7],
                gpus=gpus,
                nodelist=fields[9],                
                reason=fields[10],
            )
        )

    return jobs

