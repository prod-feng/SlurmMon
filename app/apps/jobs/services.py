from slurm.client import SlurmClient
from slurm.parsers import (
        parse_job_details,
        parse_jobs,
)

class JobService:

    SORT_FIELDS = {
        "id": "job_id",
        "user": "user",
        "partition": "partition",
        "name": "name",
        "state": "state",
        "runtime": "elapsed",
        "nodes": "nodes",
        "cpus": "cpus",
        "gpus": "gpus",
    }

    def __init__(self, client=None):
        self.client = client or SlurmClient()

    def list_jobs(
        self,
        sort="id",
        direction="asc",
    ):
        jobs = parse_jobs(
            self.client.jobs()
        )

        sort_field = self.SORT_FIELDS.get(
            sort,
            "job_id",
        )

        reverse = direction == "desc"

        if sort_field == "job_id":

            def sort_key(job):
                value = str(
                    job.job_id or ""
                ).strip()

                if value.isdigit():
                    return (
                        0,
                        int(value),
                        "",
                    )

                return (
                    1,
                    0,
                    value.lower(),
                )

        elif sort_field in (
            "nodes",
            "cpus",
        ):

            def sort_key(job):
                value = getattr(
                    job,
                    sort_field,
                    "",
                )

                try:
                    return (
                        0,
                        int(value),
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    return (
                        1,
                        0,
                    )

        elif sort_field == "gpus":

            def sort_key(job):
                value = str(
                    job.gpus or ""
                ).strip()

                if not value:
                    return (
                        0,
                        0,
                        "",
                    )

                try:
                    count = int(
                        value.rsplit(":", 1)[-1]
                    )

                    return (
                        1,
                        count,
                        value.lower(),
                    )

                except ValueError:

                    return (
                        1,
                        0,
                        value.lower(),
                    )

        else:

            def sort_key(job):
                value = getattr(
                    job,
                    sort_field,
                    "",
                )

                return str(
                    value or ""
                ).lower()

        jobs.sort(
            key=sort_key,
            reverse=reverse,
        )

        return jobs

    def get_job(self, job_id):
        output = self.client.job_details(
            job_id
        )

        return parse_job_details(
            output
        )


