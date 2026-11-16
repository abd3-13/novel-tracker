from __future__ import annotations

import logging
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from app.constants import (
    DefaultValue,
    MetadataKey,
    SettingKey,
    WebnovelErrorMessage,
    WebnovelHeader,
    WebnovelJsonKey,
)
from app.utils import db
from app.utils.images import convert_to_webp, download_image
from app.utils.tools import (
    determine_status,
    epochtohuman,
    http_get,
    normalize_height,
    normalize_text,
)

logger = logging.getLogger(__name__)

def _max_timeout() -> int:
    return int(db.get_value(SettingKey.API_TIMEOUT) or 10)


def _api_base() -> str:
    return db.get_value(SettingKey.CHARAC_API) or ""


def _img_endpoint() -> str:
    return db.get_value(SettingKey.IMG_ENDPOINT) or ""


def _character_headers() -> dict[str, str]:
    return {
        WebnovelHeader.USER_AGENT.value: db.get_value(SettingKey.USER_AGENT) or "",
        WebnovelHeader.REFERER.value: db.get_value(SettingKey.REFER_URL) or "",
        WebnovelHeader.ARCANE.value: "001030brn5eb4rAuzLLDkrMV01qxQrbDmK0wsxXjcxcJwojV95Br0af+FCtWlRsQolF/2HmbHo7jOaKWHuSxjjFexOlUf9zF6LGQLGyGnTv5I9Boj+pzAmOC5wPQEZ2r6RYrHaqvmQ/rt+AqyqHRxWMa5zOv540mOGSz/U143WnI8j/ag=",
    }


def _client_headers() -> dict[str, str]:
    return {
        WebnovelHeader.USER_AGENT.value: db.get_value(SettingKey.USER_AGENT) or "",
        WebnovelHeader.ACCEPT.value: "application/json",
        WebnovelHeader.REFERER.value: db.get_value(SettingKey.REFER_URL) or "",
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
    chapter_time: str | None
    author: str
    description: str
    status: str
    title: str | None = None
    cover: str | None = None


@dataclass(slots=True)
class CharacterInfo:
    role_id: str
    name: str
    nickname: str | None = None
    birthday: str | None = None
    height: str | None = None
    description: str | None = None
    data: dict[str, Any] | None = None


class WebnovelClient:
    def __init__(self) -> None:
        self.session = requests.Session()

    def extract_book_id(self, url: str) -> str | None:
        for pattern in BOOK_ID_PATTERNS:
            m = pattern.search(url)
            if m:
                return m.group(1)
        return None

    def fetch_latest_chapter(self, book_id: str) -> NovelInfo:
        if not book_id:
            raise ValueError(WebnovelErrorMessage.BOOK_ID_EMPTY)

        endpoint = f"{db.get_value(SettingKey.ENDPOINT)}{book_id}"

        time.sleep(
            random.uniform(
                float(db.get_value(SettingKey.DELAY_FROM) or 2),
                float(db.get_value(SettingKey.DELAY_TO) or 5),
            )
        )

        response = self.session.get(
            endpoint, headers=_client_headers(), timeout=_max_timeout()
        )
        response.raise_for_status()

        data = response.json().get(WebnovelJsonKey.DATA)
        if not data:
            raise ValueError(WebnovelErrorMessage.MISSING_RESPONSE_DATA)

        novel_status = determine_status(
            epochtohuman(data[WebnovelJsonKey.LAST_CHAPTER_TIME])
        )

        return NovelInfo(
            title=data.get(WebnovelJsonKey.BOOK_NAME),
            chapter=int(data.get(WebnovelJsonKey.CHAPTER_NUM, 0)),
            chapter_time=epochtohuman(data[WebnovelJsonKey.LAST_CHAPTER_TIME])
            if data.get(WebnovelJsonKey.LAST_CHAPTER_TIME)
            else None,
            author=data.get(WebnovelJsonKey.AUTHOR_INFO, {}).get(
                WebnovelJsonKey.AUTHOR_NAME, DefaultValue.UNKNOWN_TEXT
            ),
            description=data.get(WebnovelJsonKey.DESCRIPTION, ""),
            status=novel_status,
            cover=f"{book_id}.webp",
        )

    def enrich_from_web(self, novel: dict, book_id: str) -> None:
        info = self.fetch_latest_chapter(book_id)
        novel.update(
            {
                MetadataKey.ONLINE_CHAPTERS: info.chapter,
                MetadataKey.LATEST_CHAPTER_TIME: info.chapter_time,
                MetadataKey.AUTHOR: info.author,
                MetadataKey.DESCRIPTION: info.description,
                MetadataKey.STATUS: info.status,
                MetadataKey.TITLE: info.title,
                MetadataKey.COVER: info.cover,
            }
        )

    def get_character_list(self, book_id: str) -> list[CharacterInfo]:
        data = http_get(
            f"{_api_base()}/list",
            {WebnovelJsonKey.BOOK_ID: book_id},
            headers=_character_headers(),
            timeout=_max_timeout(),
        )
        if not data or data.get(WebnovelJsonKey.MESSAGE) != WebnovelJsonKey.SUCCESS:
            return []

        items = data.get(WebnovelJsonKey.DATA, {}).get(WebnovelJsonKey.ITEMS, [])

        return [
            CharacterInfo(
                role_id=item[WebnovelJsonKey.ROLE_ID],
                name=item.get(WebnovelJsonKey.NAME, DefaultValue.UNKNOWN_TEXT),
                data=item,
            )
            for item in items
        ]

    def count_online_characters(self, book_id: str) -> int:
        return len(self.get_character_list(book_id))

    def get_character_detail(self, book_id: str, role_id: str) -> CharacterInfo | None:
        data = http_get(
            f"{_api_base()}/detail",
            {WebnovelJsonKey.BOOK_ID: book_id, WebnovelJsonKey.ROLE_ID_FIELD: role_id},
            headers=_character_headers(),
            timeout=_max_timeout(),
        )
        if not data or data.get(WebnovelJsonKey.MESSAGE) != WebnovelJsonKey.SUCCESS:
            return None
        return normalize_character(data)

    def fetch_cover_image(
        self, book_id: str | None, overwrite: bool = False
    ) -> str | None:
        """
        Download the WebNovel cover image.
        """

        if not book_id:
            logger.warning("Cannot fetch cover without book id.")
            return None

        logger.debug("Downloading cover for %s", book_id)

        url = f"{_img_endpoint()}/cover?{WebnovelJsonKey.BOOK_ID}={book_id}"

        cover = download_image(
            url=url,
            filename=f"{book_id}.cover",
            folder=Path(
                db.get_value(SettingKey.COVER_PATH) or DefaultValue.CURRENT_DIR
            ),
            dry_run=False,
        )
        cover_file = (
            Path(db.get_value(SettingKey.COVER_PATH) or DefaultValue.CURRENT_DIR)
            / f"{book_id}.webp"
        )
        if cover:
            logger.info("Downloaded cover: %s", cover)
            convert_to_webp(image_path=cover_file, overwrite=overwrite)
        else:
            logger.warning("Cover download failed: %s", book_id)

        return cover


def normalize_character(data: dict) -> CharacterInfo:
    nickname = data.get(WebnovelJsonKey.NICKNAME)
    if isinstance(nickname, list):
        nickname = ", ".join(nickname)

    return CharacterInfo(
        role_id=data.get(WebnovelJsonKey.ROLE_ID, ""),
        name=data.get(WebnovelJsonKey.NAME) or DefaultValue.UNKNOWN_TEXT,
        nickname=nickname,
        birthday=data.get(WebnovelJsonKey.BIRTHDAY),
        height=normalize_height(data.get(WebnovelJsonKey.HEIGHT)),
        description=normalize_text(data.get(WebnovelJsonKey.DESCRIPTION, "")),
    )
