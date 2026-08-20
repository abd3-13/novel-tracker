import time


def wait_for(predicate, timeout=5, interval=0.01):
    """Wait until a predicate returns truthy or raise TimeoutError."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)

    raise TimeoutError("Timed out waiting for test condition")
