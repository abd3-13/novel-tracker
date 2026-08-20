import threading


class BlockingEngine:
    """
    Deterministic engine for cancellation tests.

    The first call blocks until `release_first` is set. This lets a test
    request cancellation while work is definitely in progress.
    """

    def __init__(self):
        self.processed = []
        self.first_started = threading.Event()
        self.release_first = threading.Event()

    def run(self, job, novel):
        novel_id = novel["id"]
        self.processed.append(novel_id)

        if len(self.processed) == 1:
            self.first_started.set()
            if not self.release_first.wait(timeout=5):
                raise TimeoutError("Timed out waiting to release first novel")

        return {
            "id": novel_id,
            "title": novel["name"],
            "updated": False,
            "changes": {},
            "errors": [],
            "warnings": [],
        }


class RecordingEngine:
    """Simple engine for tests that only need call/result recording."""

    def __init__(self):
        self.processed = []

    def run(self, job, novel):
        self.processed.append(novel["id"])
        return {
            "id": novel["id"],
            "title": novel["name"],
            "updated": False,
            "changes": {},
            "errors": [],
            "warnings": [],
        }
