from pathlib import Path
from typing import Any

from app.sync.webnovel.api import WebnovelClient
from app.utils import db

from .services import (
    count_local_characters,
    extract_epub_cover,
    get_epub_metadata,
)

_client = WebnovelClient()

# =============================================================================
# Base Provider
# =============================================================================


class BaseProvider:
    """
    Base class for all metadata providers.

    Providers expose normalized metadata through a common interface,
    regardless of where the data originates.
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self.data: dict[str, Any] = {}

    def load(self) -> None:
        """
        Load provider metadata.

        Implemented by subclasses.
        """

    def get(self, key: str, default: Any = None) -> Any:
        """
        Return a metadata value.
        """
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        """
        Check whether a metadata key exists.
        """
        return key in self.data

    def clear(self) -> None:
        """
        Clear cached metadata.
        """
        self.data.clear()


# =============================================================================
# Local Provider
# =============================================================================


class LocalProvider(BaseProvider):
    """
    Provides metadata extracted from the local EPUB.
    """

    def load(self) -> None:

        novel = self.ctx.novel

        self.ctx.logger.debug(f"Loading local metadata: {novel['name']}")

        epub_path = novel.get("filepath")

        if not epub_path:
            self.ctx.logger.warning(f"{novel['name']} has no EPUB file.")
            return

        # ---------------------------------------------------------
        # Basic EPUB metadata
        # ---------------------------------------------------------

        meta = get_epub_metadata(epub_path)

        # ---------------------------------------------------------
        # Build provider data
        # ---------------------------------------------------------

        self.data = {
            # Basic
            "title": meta.title,
            "author": meta.author,
            "description": meta.description,
            "url": meta.url,
            "source": meta.source,
            "localchap": meta.chapters,
            "local_lastchaptitle": meta.last_title,
            "local_lastchapfile": meta.last_file,
            "characters": meta.characters or count_local_characters(epub_path),
            "cover": meta.cover_id or extract_epub_cover(epub_path),
            # TODO: Add support for progress tracking in local EPUBs with Moonreader
            "progress": None,
            "progress_updated": None,
            # File
            "filepath": epub_path,
            "epub_exists": (
                Path(db.get_value("LOCAL_EPUB_DIR") or "./") / epub_path
            ).exists(),
        }

        self.ctx.logger.debug(f"Local provider loaded {len(self.data)} fields.")


# =============================================================================
# Online Provider
# =============================================================================


class OnlineProvider(BaseProvider):
    """
    Provides metadata from the online source.
    """

    def load(self) -> None:

        novel = self.ctx.novel

        self.ctx.logger.debug(f"Loading online metadata: {novel['name']}")

        url = novel.get("url")

        source = novel.get("source")

        if source != "webnovel":
            return

        if not url:
            return

        book_id = _client.extract_book_id(url)

        if not book_id:
            self.ctx.logger.warning(f"No WebNovel book id for '{novel['name']}'")
            return

        info = _client.fetch_latest_chapter(book_id)

        self.ctx.logger.debug(f"Fetched WebNovel metadata ({book_id})")

        self.data = {
            # Basic
            "title": info.title,
            "author": info.author,
            "description": info.description,
            "url": url,
            "source": "webnovel",
            # Chapters
            "onlinechap": info.chapter,
            "latestchaptime": info.chapter_time,
            # Characters
            "online_characters": _client.count_online_characters(book_id),
            # Status
            "status": info.status,
            # Cover
            "cover": info.cover,
        }

        self.ctx.logger.debug(f"Online provider loaded {len(self.data)} fields.")


# =============================================================================
# Provider Manager
# =============================================================================


class ProviderManager:
    """
    Coordinates metadata providers.

    Responsible for:

    - Registering providers
    - Loading providers
    - Returning metadata values
    """

    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register(self, source: str, provider: BaseProvider) -> None:
        """
        Register a provider.
        """
        self._providers[source] = provider

    # -------------------------------------------------------------------------
    # Provider access
    # -------------------------------------------------------------------------

    def get_provider(self, source: str) -> BaseProvider | None:
        """
        Return the provider for a source.
        """
        return self._providers.get(source)

    # -------------------------------------------------------------------------
    # Loading
    # -------------------------------------------------------------------------

    def load_all(self) -> None:
        """
        Load all registered providers.
        """
        for name, provider in self._providers.items():
            provider.ctx.logger.debug(f"Loading provider '{name}'")

            provider.load()

    # -------------------------------------------------------------------------
    # Value lookup
    # -------------------------------------------------------------------------

    def get_value(self, source: str, field):
        """
        Return the metadata value for a field using the
        specified source.

        Example:

            get_value("online", author_field)
        """

        provider = self.get_provider(source)

        if provider is None:
            return None

        attribute = field.sources.get(source)

        value = provider.get(attribute)

        return value

    def get_value_from(self, source: str, field):
        """
        Explicitly fetch a value from a specific source.

        Alias for get_value(), intended for special metadata
        handlers such as cover synchronization.
        """
        return self.get_value(source, field)
