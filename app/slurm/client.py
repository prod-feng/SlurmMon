import os
import subprocess

from django.conf import settings

from .exceptions import (
    SlurmCommandError,
    SlurmTimeoutError,
)


class SlurmClient:
    """
    Safe wrapper around Slurm CLI commands.

    No shell=True is used.
    Commands and arguments are passed as an argv list.
    """

    def __init__(
        self,
        slurm_bin: str | None = None,
        timeout: int | None = None,
    ):
        self.slurm_bin = slurm_bin or settings.SLURM_BIN
        self.timeout = timeout or settings.SLURM_TIMEOUT

    def _run(self, executable: str, *args: str) -> str:
        command = os.path.join(self.slurm_bin, executable)

        try:
            result = subprocess.run(
                [command, *args],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SlurmTimeoutError(
                f"{executable} timed out"
            ) from exc

        if result.returncode != 0:
            raise SlurmCommandError(
                result.stderr.strip()
                or f"{executable} failed with code {result.returncode}"
            )

        return result.stdout

    def nodes(self) -> str:
        return self._run(
            "sinfo",
            "-N",
            "-h",
            "-o",
            "%N|%T|%C|%m|%G|%P",
        )

    def partitions(self) -> str:
        return self._run(
            "sinfo",
            "-h",
            "-o",
            "%P|%a|%l|%D|%C",
        )

    def jobs(self) -> str:
        return self._run(
            "squeue",
            "-h",
            "-o",
            "%i|%u|%P|%j|%T|%M|%D|%R",
        )

    def cluster_status(self) -> str:
        return self._run(
            "sinfo",
            "-h",
            "-o",
            "%F|%C|%m",
        )

    def node_details(self, node: str) -> str:
        return self._run(
            "scontrol",
            "show",
            "node",
            node,
        )

    def drain_node(self, node: str, reason: str) -> str:
        return self._run(
            "scontrol",
            "update",
            f"NodeName={node}",
            "State=DRAIN",
            f"Reason={reason}",
        )

    def resume_node(self, node: str) -> str:
        return self._run(
            "scontrol",
            "update",
            f"NodeName={node}",
            "State=RESUME",
        )

