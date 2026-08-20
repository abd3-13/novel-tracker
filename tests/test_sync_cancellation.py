import threading

from app.sync.job import SyncJob
from app.sync.runner import SyncRunner


class FakeEngine:
    def __init__(self):
        self.processed = []
        self.first_novel_started = threading.Event()
        self.allow_first_novel_to_finish = threading.Event()

    def run(self, job, novel):
        novel_id = novel["id"]
        self.processed.append(novel_id)

        if novel_id == 1:
            self.first_novel_started.set()
            self.allow_first_novel_to_finish.wait(timeout=5)

        return {
            "novel_id": novel_id,
            "success": True,
            "errors": [],
            "warnings": [],
        }


def main():
    novels = [
        {"id": 1, "name": "Novel One"},
        {"id": 2, "name": "Novel Two"},
        {"id": 3, "name": "Novel Three"},
    ]

    engine = FakeEngine()

    runner = SyncRunner()
    runner.engine = engine

    cancelled = threading.Event()
    events = []

    job = SyncJob(
        novels=[novel["id"] for novel in novels],
        fields=[],
    )

    def is_cancelled():
        return cancelled.is_set()

    def on_event(event):
        events.append(event)
        print(f"EVENT: {event}")

    def run():
        result = runner.run(
            job,
            novels=novels,
            is_cancelled=is_cancelled,
            on_event=on_event,
        )

        print("\nRESULT:")
        print(result)

    thread = threading.Thread(target=run)
    thread.start()

    # Wait until novel 1 has actually started.
    if not engine.first_novel_started.wait(timeout=5):
        raise RuntimeError("Novel 1 never started")

    print("\n>>> Requesting cancellation")

    # Request cancellation while novel 1 is running.
    cancelled.set()

    # Allow the currently running novel to finish.
    engine.allow_first_novel_to_finish.set()

    thread.join(timeout=10)

    if thread.is_alive():
        raise RuntimeError("Runner did not finish after cancellation")

    print("\nPROCESSED NOVELS:")
    print(engine.processed)

    print("\nASSERTIONS:")

    assert engine.processed == [1], (
        f"Expected only novel 1 to be processed, got {engine.processed}"
    )

    assert any("cancel" in str(event).lower() for event in events), (
        "No cancellation event was emitted"
    )

    print("✓ Current novel was allowed to finish")
    print("✓ Cancellation was detected")
    print("✓ Remaining novels were not processed")
    print("✓ Cancellation event was emitted")
    print("\nCANCELLATION TEST PASSED")


if __name__ == "__main__":
    main()
