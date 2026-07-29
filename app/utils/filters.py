import logging
import re
from datetime import datetime

# Regular expression for the expected date format '%Y-%m-%d %H:%M:%S.%f'
DATE_FORMAT_REGEX = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"


def time_difference(latest_time_str: str | None) -> int:
    if latest_time_str in (None, "", "0"):
        return 999999  # or another default value you prefer

    if not re.match(DATE_FORMAT_REGEX, latest_time_str):
        return 999999

    latest_time = datetime.strptime(latest_time_str, "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    delta = now - latest_time
    days = delta.days

    return int(days if days > 0 else 1)


# Remove some logs from repated spam of the log stream
SPAM_PATHS = ["/status", "/ping", "/health", "/static/img/cover", "/receive-cookie"]


class log_SpamFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        return not any(p in msg and " 200 " in msg for p in SPAM_PATHS)
