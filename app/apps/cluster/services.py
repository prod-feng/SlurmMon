from slurm.client import SlurmClient


class ClusterService:
    def __init__(self, client=None):
        self.client = client or SlurmClient()

    def status(self):
        output = self.client.cluster_status()

        lines = []

        for line in output.splitlines():
            fields = line.split("|")

            if len(fields) == 3:
                lines.append(
                    {
                        "nodes": fields[0],
                        "cpus": fields[1],
                        "memory": fields[2],
                    }
                )

        return lines

