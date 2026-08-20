# Novel Tracker v2 Testing

The test suite uses `pytest` and is divided by responsibility.

## Structure

```text
tests/
├── conftest.py
├── support/
│   └── fakes.py
├── unit/
│   ├── test_execution.py
│   └── test_runner.py
└── integration/
    └── test_sync_manager.py
```

### Unit tests

Unit tests isolate one synchronization component. They do not require a real
SQLite database, EPUB files, WebNovel access, or a running Flask server.

### Integration tests

Integration tests exercise multiple synchronization components together. The
manager tests use deterministic fake engines, so cancellation tests do not
rely on arbitrary `sleep()` timing.

## Running

Run everything:

```bash
python -m pytest
```

Run only unit tests:

```bash
python -m pytest -m unit
```

Run only integration tests:

```bash
python -m pytest -m integration
```

Run cancellation tests:

```bash
python -m pytest -k cancellation
```

Run a single test with full output:

```bash
python -m pytest tests/integration/test_sync_manager.py -vv -s
```
