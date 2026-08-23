class SlurmError(Exception):
    """Base exception for Slurm integration."""


class SlurmCommandError(SlurmError):
    """Slurm command returned a non-zero exit code."""


class SlurmTimeoutError(SlurmError):
    """Slurm command timed out."""

