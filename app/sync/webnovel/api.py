from __future__ import annotations

import logging
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests

import app.utils.db as db
from app.utils.tools import (
    determine_status,
    epochtohuman,
    http_get,
    normalize_height,
    normalize_text,
)

logger = logging.getLogger(__name__)

MAX_TIMEOUT = int(db.get_value("API_TIMEOUT") or 10)

API_BASE = "https://idruid.webnovel.com/go/api/book-role"

CHARACTER_HEADERS = {
    "User-Agent": "Mozilla/mobile QDHWReaderAndroid/8.15.3/1153/2000002/ffffffff95ab80ef0000000073051a64",
    "Referer": "https://android.webnovel.com",
    "arcane": "001030brn5eb4rAuzLLDkrMV01qxQrbDmK0wsxXjcxcJwojV95Br0af+FCtWlRsQolF/2HmbHo7jOaKWHuSxjjFexOlUf9zF6LGQLGyGnTv5I9Boj+pzAmOC5wPQEZ2r6RYrHaqvmQ/rt+AqyqHRxWMa5zOv540mOGSz/U143WnI8j/ag=",
}

BOOK_ID_PATTERNS = (
    re.compile(r"_(\d{8,})$"),
    re.compile(r"/book/(\d{8,})"),
    re.compile(r"(\d{8,})"),
)


class NetworkError(Exception):
    """Raised when a network request fails."""


@dataclass(slots=True)
class NovelInfo:
    chapter: int
    chapter_time: Optional[str]
    author: str
    description: str
    status: str
    title: str | None = None
    cover: Optional[str] = None


@dataclass(slots=True)
class CharacterInfo:
    role_id: str
    name: str
    nickname: str | None = None
    birthday: str | None = None
    height: str | None = None
    description: str | None = None
    image_url: str | None = None
    data: dict[str, Any] | None = None


class WebnovelClient:
    def __init__(self) -> None:
        self.session = requests.Session()

    def extract_book_id(self, url: str) -> Optional[str]:
        for pattern in BOOK_ID_PATTERNS:
            m = pattern.search(url)
            if m:
                return m.group(1)
        return None

    def fetch_latest_chapter(self, book_id: str) -> NovelInfo:
        if not book_id:
            raise ValueError("book_id cannot be empty")

        endpoint = f"{db.get_value('ENDPOINT')}{book_id}"
        headers = {
            "User-Agent": db.get_value("USER_AGENT"),
            "Accept": "application/json",
            "Referer": "https://android.webnovel.com",
        }

        time.sleep(
            random.uniform(
                float(db.get_value("DELAY_FROM") or 2),
                float(db.get_value("DELAY_TO") or 5),
            )
        )

        response = self.session.get(endpoint, headers=headers, timeout=MAX_TIMEOUT)
        response.raise_for_status()

        data = response.json().get("Data")
        if not data:
            raise ValueError("Missing 'Data' in API response.")

        novel_status = determine_status(epochtohuman(data["LastChapterTime"]))

        return NovelInfo(
            title=data.get("BookName"),
            chapter=int(data.get("ChapterNum", 0)),
            chapter_time=epochtohuman(data["LastChapterTime"])
            if data.get("LastChapterTime")
            else None,
            author=data.get("AuthorInfo", {}).get("AuthorName", "Unknown"),
            description=data.get("Description", ""),
            status=novel_status,
            cover=f"{book_id}.webp",
        )

    def enrich_from_web(self, novel: dict, book_id: str) -> None:
        info = self.fetch_latest_chapter(book_id)
        novel.update(
            {
                "onlinechap": info.chapter,
                "latestchaptime": info.chapter_time,
                "author": info.author,
                "description": info.description,
                "status": info.status,
                "name": info.title,
                "cover": info.cover,
            }
        )

    def get_character_list(self, book_id: str) -> list[CharacterInfo]:
        data = http_get(
            f"{API_BASE}/list",
            {"bookId": book_id},
            headers=CHARACTER_HEADERS,
            timeout=MAX_TIMEOUT,
        )
        if not data or data.get("Message") != "Success":
            return []

        items = data.get("Data", {}).get("Items", [])

        return [
            CharacterInfo(
                role_id=item["RoleId"], name=item.get("Name", "Unknown"), data=item
            )
            for item in items
        ]

    def count_online_characters(self, book_id: str) -> int:
        return len(self.get_character_list(book_id))

    def get_character_detail(
        self, book_id: str, role_id: str
    ) -> Optional[CharacterInfo]:
        data = http_get(
            f"{API_BASE}/detail",
            {"bookId": book_id, "roleId": role_id},
            headers=CHARACTER_HEADERS,
            timeout=MAX_TIMEOUT,
        )
        if not data or data.get("Message") != "Success":
            return None
        return normalize_character(data)


def normalize_character(data: dict) -> CharacterInfo:
    nickname = data.get("NickName")
    if isinstance(nickname, list):
        nickname = ", ".join(nickname)

    return CharacterInfo(
        role_id=data.get("RoleId", ""),
        name=data.get("Name") or "Unknown",
        nickname=nickname,
        birthday=data.get("Birthday"),
        height=normalize_height(data.get("Height")),
        description=normalize_text(data.get("Description", "")),
        image_url=data.get("DesignImage"),
    )
