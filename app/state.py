import time
from threading import Lock

class BulkState:
    def __init__(self):
        self.progress_lock = Lock()
        self.run_lock = Lock()
        self._reset_nolock()

    def _reset_nolock(self):
        self.cancel = False
        self.data = {
            "current": 0,
            "total": 0,
            "failed": 0,
            "message": "Idle",
            "logs": [],
            "done": True,
            "start_time": None,
            "eta": None,
        }

    def start(self):
        with self.progress_lock:
            self._reset_nolock()
            self.data["done"] = False
            self.data["start_time"] = time.time()
            self.data["message"] = "Starting..."

    def update(self, **kwargs):
        with self.progress_lock:
            self.data.update(kwargs)

    def finish(self):
        with self.progress_lock:
            self.data["done"] = True
            self.data["message"] = "Completed"

    def snapshot(self):
        with self.progress_lock:
            return dict(self.data)
