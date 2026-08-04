from pathlib import Path
from typing import Any

from app.constants import Asset, Event, MetadataKey
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
        self.novel = ctx.novel
        self.filepath = self.novel.get(MetadataKey.FILEPATH)
        self.url = self.novel.get(MetadataKey.URL)
        self.source = self.novel.get(MetadataKey.SOURCE)

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

        self.ctx.logger.debug(
            f"Loading local metadata: {self.novel[MetadataKey.TITLE]}"
        )

        if not self.filepath:
            self.ctx.logger.warning(
                f"{self.novel[MetadataKey.TITLE]} has no EPUB file."
            )
            return

        # ---------------------------------------------------------
        # Basic EPUB metadata
        # ---------------------------------------------------------

        self.meta = get_epub_metadata(self.filepath)

        # ---------------------------------------------------------
        # MoonReader progress
        # ---------------------------------------------------------
        progress = None
        try:
            progress = get_moonreader_progress(self.filepath)
        except Exception as e:  # noqa: BLE001
            self.ctx.logger.error(
                f"Error fetching MoonReader progress for {self.novel[MetadataKey.TITLE]}: {e}"
            )

        # ---------------------------------------------------------
        # Build provider data
        # ---------------------------------------------------------

        self.data = {
            MetadataKey.TITLE: self.meta.title,
            MetadataKey.AUTHOR: self.meta.author,
            MetadataKey.DESCRIPTION: self.meta.description,
            MetadataKey.URL: self.meta.url,
            MetadataKey.SOURCE: self.meta.source,
            MetadataKey.LOCAL_CHAPTERS: self.meta.chapters,
            MetadataKey.LOCAL_LAST_TITLE: self.meta.last_title,
            MetadataKey.LOCAL_LAST_FILE: self.meta.last_file,
            MetadataKey.CHARACTERS: self.meta.characters,
            MetadataKey.COVER: self.meta.cover_id,
            MetadataKey.PROGRESS: progress.chapter if progress is not None else None,
            MetadataKey.FILEPATH: self.filepath,
            MetadataKey.EPUB_EXISTS: (
                Path(db.get_value("LOCAL_EPUB_DIR") or "./") / self.filepath
            ).exists(),
        }

        self.ctx.logger.debug(f"Local provider loaded {len(self.data)} fields.")

    def fetch_cover(self):
        """
        Fetch the cover image from the EPUB.
        """

        self.ctx.logger.info("Fetching local cover...")
        self.ctx.emit(Event.ASSET, asset=Asset.COVER)

        cover = extract_epub_cover(self.filepath)

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

    def __init__(self, ctx):
        super().__init__(ctx)
        self.book_id = _client.extract_book_id(self.url or "")

    def load(self) -> None:

        self.ctx.logger.debug(
            f"Loading online metadata: {self.novel[MetadataKey.TITLE]}"
        )

        if self.source != "webnovel":
            return

        if not self.url:
            return

        book_id = self.book_id

        if not book_id:
            self.ctx.logger.warning(
                f"No WebNovel book id for '{self.novel[MetadataKey.TITLE]}', skipping online provider."
            )
            return

        info = _client.fetch_latest_chapter(book_id)

        self.ctx.logger.debug(f"Fetched WebNovel metadata ({book_id})")

        self.data = {
            # Basic
            MetadataKey.TITLE: info.title,
            MetadataKey.AUTHOR: info.author,
            MetadataKey.DESCRIPTION: info.description,
            MetadataKey.URL: self.url,
            MetadataKey.SOURCE: "webnovel",
            MetadataKey.ONLINE_CHAPTERS: info.chapter,
            MetadataKey.LATEST_CHAPTER_TIME: info.chapter_time,
            MetadataKey.ONLINE_CHARACTERS: _client.count_online_characters(book_id),
            MetadataKey.STATUS: info.status,
            MetadataKey.COVER: info.cover,
            MetadataKey.FILEPATH: self.filepath,
        }

        self.ctx.logger.debug(f"Online provider loaded {len(self.data)} fields.")

    def fetch_cover(self):
        """
        Fetch the cover image from the online source.
        """

        self.ctx.logger.info("Fetching online cover...")
        self.ctx.emit(Event.ASSET, asset=Asset.COVER)
        cover = _client.fetch_cover_image(self.book_id)

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

        output_dir = Path(db.get_value("LOCAL_EPUB_DIR") or "./") / self.filepath
        self.ctx.emit(Event.ASSET, asset=Asset.CHARACTERS)
        result = WN_fetch_characters(book_id=self.book_id, output_dir=output_dir)

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
