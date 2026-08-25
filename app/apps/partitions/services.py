from slurm.client import SlurmClient
from slurm.parsers import (
        parse_partition_details,
        parse_partitions,
)        


class PartitionService:
    def __init__(self, client=None):
        self.client = client or SlurmClient()

    def list_partitions(self):
        return parse_partitions(
            self.client.partitions()
        )

    def get_partition_details(self, partition_name):
        output = self.client.partition_details(
            partition_name
        )

        return parse_partition_details(output)

