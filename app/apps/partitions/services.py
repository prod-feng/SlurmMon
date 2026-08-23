from slurm.client import SlurmClient
from slurm.parsers import parse_partitions


class PartitionService:
    def __init__(self, client=None):
        self.client = client or SlurmClient()

    def list_partitions(self):
        return parse_partitions(
            self.client.partitions()
        )

