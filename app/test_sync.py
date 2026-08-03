"""
End-to-end test for the synchronization engine.

Run:

    python -m app.test_sync
"""

from app.sync.bulk import synchronize
from app.sync.job import SyncJob, SyncMode


def main():

    # ----------------------------------------------------------
    # Synchronization job
    # ----------------------------------------------------------

    job = SyncJob(
        table="demo_novels",
        source="local",
        mode=SyncMode.ONLY_CHANGED,
        fields=[
            "title",
            "author",
            "description",
            "localchap",
            "local_lastchaptitle",
            "local_lastchapfile",
            "cover",
            "filepath",
            "status",
        ],
        novels=[13],
    )

    # ----------------------------------------------------------
    # Execute
    # ----------------------------------------------------------

    print("\n===== Synchronize =====")

    results = synchronize(job)

    print("\n===== Results =====")

    for result in results:
        print(result)


if __name__ == "__main__":
    main()
