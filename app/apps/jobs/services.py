from slurm.client import SlurmClient
from slurm.parsers import parse_jobs


class JobService:
    def __init__(self, client=None):
        self.client = client or SlurmClient()

    def list_jobs(self):
        return parse_jobs(
            self.client.jobs()
        )

