import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlparse

from curl_cffi import requests

from app.constants import Asset, DefaultValue
from app.utils.filters import time_difference

bulk_progress = {
    "total": 0,
    "current": 0,
    "failed": 0,
    "message": "",
    "logs": [],  # per-item log lines (new)
    "start_time": None,  # timestamp when job started
    "eta": None,  # seconds remaining (computed)
    "done": False,
    "delay": "",
}
bulk_cancel_flag = False

progress_lock = Lock()
bulk_run_lock = Lock()


def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result

    return wrapper


def url_domain(url=None):
    if url:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return domain
    return False


def parse_moonreader_progress(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    progress_map = {}

    for node in root.findall("string"):
        full_path = node.attrib.get("name", "")
        value = (node.text or "").strip()

        # filename only
        filename = normalize_filename(os.path.basename(full_path))

        # Match: 242@0#263:36.4%
        m = re.match(r"(\d+)@.*?:([\d.]+)%", value)
        if not m:
            continue

        chapter = int(m.group(1))

        progress_map[filename] = {"chapter": chapter}

    return progress_map


def epochtohuman(epochtime):
    return datetime.fromtimestamp(epochtime / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def timenow():
    return datetime.now(tz=timezone.utc).replace(microsecond=0)


def determine_status(latest_chap_time):
    if not latest_chap_time or latest_chap_time == "0":
        return DefaultValue.UNKNOWN_TEXT
    time_diff = time_difference(latest_chap_time)
    return DefaultValue.ONGOING if time_diff <= 30 else DefaultValue.HIATUS


def normalize_tags(tag_string: str) -> str:
    if not tag_string:
        return ""

    tags = {t.strip().lower() for t in tag_string.split(",") if t.strip()}

    return ",".join(sorted(tags))


def normalize_title(title: str) -> str:
    title = title.strip().lower()
    title = re.sub(r"[^\w\s]", "", title)  # remove punctuation
    title = re.sub(r"\s+", " ", title)
    return title


def sanitize_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    return re.sub(r"[^\w\-]", "", name)


def normalize_filename(name):
    name = name.lower()
    name = re.sub(r"\s*c\d+\.epub$", ".epub", name)
    name = re.sub(r"\.epub$", "", name)
    name = re.sub(r"c\d+", "", name)  # remove c47, c123
    name = re.sub(r"chapter\s*\d+", "", name)
    name = re.sub(r"[^a-z0-9]", "", name)  # remove symbols
    name = name.replace("_", " ")
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def normalize_text(text: str) -> str:
    """Convert multiline / messy text into a single clean line."""
    if not text:
        return ""

    # Replace newlines and tabs with spaces
    text = re.sub(r"[\r\n\t]+", " ", text)

    # Collapse multiple spaces
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


def normalize_height(height):
    """
    Normalize height to centimeters.
    Supports cm, feet+inches, inches.
    """
    if not height:
        return None

    text = str(height).lower().strip()

    # Already in cm
    cm_match = re.search(r"(\d+(?:\.\d+)?)\s*cm", text)
    if cm_match:
        return f"{cm_match.group(1)} cm"

    # Feet and inches (5'7", 5 ft 7 in, 5-7)
    ft_in_match = re.search(r"(\d+)\s*(?:ft|')\s*(\d+)?\s*(?:in|\")?", text)
    if not ft_in_match:
        ft_in_match = re.search(r"(\d+)\s*[-]\s*(\d+)", text)

    if ft_in_match:
        ft = int(ft_in_match.group(1))
        inch = int(ft_in_match.group(2) or 0)
        cm = round((ft * 12 + inch) * 2.54)
        return f"{cm} cm"

    # Inches only
    in_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:in|inch)", text)
    if in_match:
        cm = round(float(in_match.group(1)) * 2.54)
        return f"{cm} cm"

    # Plain number (assume cm if reasonable)
    if text.isdigit():
        value = int(text)
        if 100 <= value <= 250:
            return f"{value} cm"

    # Fallback: return original
    return height


def character_to_html_line(character: dict) -> str:
    """
    Convert character dict to a single-line HTML-like string.
    Name in <b>, other fields separated by <br/>.
    """
    name = character.get("name", DefaultValue.UNKNOWN_TEXT)

    parts = [f"<b>{name}</b>"]

    for key, label in [
        ("nickname", "Nickname"),
        ("birthday", "Birthday"),
        ("height", "Height"),
        ("description", "Description"),
    ]:
        value = character.get(key)
        if value:
            parts.append(f"{label}: {value}")

    return "<br/>".join(parts)


def write_characters_json(characters: list[dict], output_dir: Path):
    character_file = f"{Asset.CHARACTERS.value}.json"
    with open(output_dir / character_file, "w", encoding="utf8") as f:
        json.dump(characters, f, indent=2, ensure_ascii=False)


def write_characters_txt(characters: list[dict], output_dir: Path):
    character_file = f"{Asset.CHARACTERS.value}.txt"
    with open(output_dir / character_file, "w", encoding="utf-8") as f:
        f.writelines(character_to_html_line(char) + "\n" for char in characters)


def http_get(
    url: str,
    params: dict[str, Any] | None = None,
    retries: int = 3,
    initial_delay: float = 2.0,
    headers: dict[str, str] | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    delay = initial_delay

    for attempt in range(1, retries + 1):
        try:
            r = requests.get(
                url,
                params=params,
                headers=headers,
                impersonate="chrome_android",
                timeout=timeout,
            )
            r.raise_for_status()
            return r.json()

        except KeyboardInterrupt:
            raise

        except Exception as exc:
            print(f"  [WARN] API request failed ({attempt}/{retries}): {exc}")

            if attempt == retries:
                raise RuntimeError(
                    f"API request failed after {retries} attempts"
                ) from exc

            time.sleep(delay)
            delay *= 2

    raise RuntimeError("Unreachable")
