import json
from queue import Queue

import pytest
from flask import Flask

from app.routes.main import _sync_event_stream

pytestmark = pytest.mark.unit


class FakeExecution:
    def __init__(self, events, done=False):
        self.events = events
        self.done = done

    def snapshot(self):
        return {"done": self.done}


class FakeEvent:
    type = "field"
    data = object()


def test_sync_event_stream_reports_serialization_errors():
    events = Queue()
    events.put(FakeEvent())

    app = Flask(__name__)

    with app.app_context():
        frames = list(_sync_event_stream(FakeExecution(events)))

    error_frame = next(frame for frame in frames if frame.startswith("event: error"))
    payload = json.loads(error_frame.split("data: ", 1)[1])

    assert payload == {
        "message": "Failed to serialize synchronization event.",
        "event": "field",
    }


def test_sync_event_stream_finishes_when_execution_is_done():
    app = Flask(__name__)

    with app.app_context():
        frames = list(_sync_event_stream(FakeExecution(Queue(), done=True), timeout=0.01))

    assert frames == ['event: done\ndata: {"done": true}\n\n']
