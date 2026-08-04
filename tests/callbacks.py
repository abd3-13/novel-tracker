from app.sync.events import SyncEvent


def print_events(event: SyncEvent):
    """
    Simple event printer.
    """

    print(f"[{event.type.upper()}] {event.data}")


def quiet(event: SyncEvent):
    """
    Ignore events.
    """
