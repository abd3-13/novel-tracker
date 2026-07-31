"""
Public synchronization API.

This module is the entry point used by:

- Flask routes
- CLI commands
- Scheduled jobs
- Future background workers

It delegates execution to SyncRunner.
"""

from .runner import SyncRunner


def synchronize(job):
    """
    Execute a synchronization job.

    Parameters
    ----------
    job : SyncJob
        Synchronization request.

    Returns
    -------
    list[dict]
        Result for every processed novel.
    """

    runner = SyncRunner()

    return runner.run(job)


def preview(job):
    """
    Preview which novels would be synchronized.

    No metadata is downloaded.
    No database updates are performed.
    """

    runner = SyncRunner()

    return runner.preview(job)
