"""
Simple test for providers.py

Run:

    python test_sync.py
"""

import app.utils.db as db
from app.sync.context import SyncContext
from app.sync.engine import SyncEngine
from app.sync.job import SyncJob
from app.sync.providers import LocalProvider


def print_provider(provider):
    print(f"\n===== {provider.__class__.__name__} =====")

    provider.load()

    if not provider.data:
        print("No data loaded.")
        return

    for key, value in provider.data.items():
        print(f"{key:25} : {value}")


def test_engine(job, novel):
    print("\n===== SyncEngine =====")

    engine = SyncEngine(db)

    result = engine.run(job, novel)

    print("\n===== Engine Result =====")

    if not result:
        print("No updates.")
        return

    for key, value in result.items():
        print(f"{key:25} : {value}")


def main():

    # ----------------------------------------------------------
    # Pick a novel from database
    # ----------------------------------------------------------

    novel = db.fetch_one("SELECT * FROM demo_novels WHERE id is 13")

    if novel is None:
        print("No novel found.")
        return

    # sqlite tuple -> dict
    columns = [
        "id",
        "name",
        "url",
        "localchap",
        "onlinechap",
        "latestchaptime",
        "status",
        "source",
        "notes",
        "filepath",
        "created_time",
        "last_updated",
        "updated_count",
        "epub_exists",
        "author",
        "description",
        "tags",
        "characters",
        "online_characters",
        "cover_path",
        "local_lastchaptitle",
        "local_lastchapfile",
        "progress",
        "progress_updated",
    ]

    novel = dict(zip(columns, novel))

    print("\n===== DatabaseData =====")

    for key, value in novel.items():
        print(f"{key:25} : {value}")

    # ----------------------------------------------------------
    # Dummy Sync Job
    # ----------------------------------------------------------

    job = SyncJob(
        table="demo_novels",
        source="local",
        fields=["title", "author", "description", "localchap"],
        mode="overwrite",
    )

    ctx = SyncContext(job=job, novel=novel)

    # ----------------------------------------------------------
    # Test Local Provider
    # ----------------------------------------------------------

    print_provider(LocalProvider(ctx))
    test_engine(job, novel)


if __name__ == "__main__":
    main()
