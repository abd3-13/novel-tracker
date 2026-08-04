from app.constants import LogLevel, SyncAction

# =============================================================================
# Logger
# =============================================================================


class SyncLogger:
    """
    Console logger for the synchronization engine.

    Later this can be replaced with:
        - WebSocket logger
        - Flask logger
        - File logger
        - Rich console logger

    without changing the synchronization engine.
    """

    def __init__(self, level=LogLevel.NORMAL):
        self.level = level
        self.errors = []
        self.warnings = []

    # ------------------------------------------------------------------
    # Generic logging
    # ------------------------------------------------------------------

    def info(self, message):
        if self.level in (LogLevel.NORMAL, LogLevel.DEBUG):
            print(message)

    def debug(self, message):
        if self.level == LogLevel.DEBUG:
            print(message)

    def warning(self, message):
        if self.level != LogLevel.SILENT:
            self.warnings.append(message)
            print(f"[WARNING] {message}")

    def error(self, message):
        if self.level != LogLevel.SILENT:
            self.errors.append(message)
            print(f"[ERROR] {message}")

    # ------------------------------------------------------------------
    # Synchronization helpers
    # ------------------------------------------------------------------

    def job(self, title):
        self.info(f"\n===== {title} =====")

    def provider(self, name):
        self.debug(f"\nLoading provider: {name}")

    def progress(self, current, total, title):
        self.info(f"\n[{current}/{total}] {title}")

    def collector(self, updates):

        self.debug("\n===== SyncCollector =====")

        if not updates:
            self.debug("No updates.")
            return

        for key, value in updates.items():
            self.debug(f"{key:25} : {value}")

    def field(self, column, current, new, update):

        if self.level != LogLevel.DEBUG:
            return

        action = SyncAction.UPDATE if update else SyncAction.SKIP

        print(f"{column:25}{str(current)[:40]:40}{str(new)[:40]:40}{action}")

    def summary(self, processed, updated, skipped, errors, warnings):

        self.info("\n===== Summary =====")
        self.info(f"Processed : {processed}")
        self.info(f"Updated   : {updated}")
        self.info(f"Skipped   : {skipped}")
        self.info(f"Errors    : {errors}")
        self.info(f"Warnings  : {warnings}")
