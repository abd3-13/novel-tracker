from pathlib import Path
from typing import Any

from app.sync.services import (
    extract_epub_cover,
    get_epub_metadata,
    get_moonreader_progress,
)
from app.sync.webnovel.api import WebnovelClient
from app.sync.webnovel.character_service import fetch_characters as WN_fetch_characters
from app.utils import db

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

    def fetch_cover(self):
        raise NotImplementedError

    def fetch_characters(self):
        raise NotImplementedError


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

        self.meta = get_epub_metadata(epub_path)

        # ---------------------------------------------------------
        # MoonReader progress
        # ---------------------------------------------------------
        progress = get_moonreader_progress(epub_path)

        # ---------------------------------------------------------
        # Build provider data
        # ---------------------------------------------------------

        self.data = {
            "title": self.meta.title,
            "author": self.meta.author,
            "description": self.meta.description,
            "url": self.meta.url,
            "source": self.meta.source,
            "localchap": self.meta.chapters,
            "local_lastchaptitle": self.meta.last_title,
            "local_lastchapfile": self.meta.last_file,
            "characters": self.meta.characters,
            "cover": self.meta.cover_id,
            "progress": progress.chapter,
            "filepath": epub_path,
            "epub_exists": (
                Path(db.get_value("LOCAL_EPUB_DIR") or "./") / epub_path
            ).exists(),
        }

        self.ctx.logger.debug(f"Local provider loaded {len(self.data)} fields.")

    def fetch_cover(self):
        """
        Fetch the cover image from the EPUB.
        """

        epub_file = self.ctx.novel.get("filepath")

        self.ctx.logger.info("Fetching local cover...")

        cover = extract_epub_cover(epub_file)

        if cover:
            self.ctx.logger.info(f"Cover ready: {cover}")
        else:
            self.ctx.logger.warning("Cover extraction failed.")

        return cover


# =============================================================================
# Online Provider
# =============================================================================


class OnlineProvider(BaseProvider):
    """
    Provides metadata from the online source.
    """

    def _book_id(self):
        return _client.extract_book_id(self.ctx.novel.get("url", ""))

    def load(self) -> None:

        novel = self.ctx.novel

        self.ctx.logger.debug(f"Loading online metadata: {novel['name']}")

        url = novel.get("url")

        source = novel.get("source")

        if source != "webnovel":
            return

        if not url:
            return

        book_id = self._book_id()

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
            "filepath": novel.get("filepath"),
        }

        self.ctx.logger.debug(f"Online provider loaded {len(self.data)} fields.")

    def fetch_cover(self):
        """
        Fetch the cover image from the online source.
        """

        self.ctx.logger.info("Fetching online cover...")

        cover = _client.fetch_cover_image(self._book_id())

        if cover:
            self.ctx.logger.info(f"Cover ready: {cover}")
        else:
            self.ctx.logger.warning("Failed to fetch cover.")

        return cover

    def fetch_characters(self):
        """
        Fetch the list of characters from the online source.
        """

        self.ctx.logger.info("Fetching characters...")

        epub_file = self.ctx.novel.get("filepath")

        output_dir = Path(db.get_value("LOCAL_EPUB_DIR") or "./") / epub_file

        result = WN_fetch_characters(book_id=self._book_id(), output_dir=output_dir)

        self.ctx.logger.info(
            f"Characters: {result['characters']} "
            f"Downloaded: {result['downloaded']} "
            f"Failed: {result['failed']}"
        )

        return result


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

    def load(self, source: str) -> None:
        """
        Load a single provider.
        """

        provider = self.get_provider(source)

        if provider is None:
            raise ValueError(f"No provider registered for '{source}'")

        provider.ctx.logger.debug(f"Loading provider '{source}'")

        provider.load()

    def load_all(self) -> None:
        """
        Load all registered providers.
        """

        for source in self._providers:
            self.load(source)

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
