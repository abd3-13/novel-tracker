from pathlib import Path
from typing import Any

from app.constants import (
    Asset,
    DefaultValue,
    Event,
    MetadataKey,
    SettingKey,
    SourceDomain,
)
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
            self.data = {MetadataKey.EPUB_EXISTS: False}
            return

        epub_path = (
            Path(db.get_value(SettingKey.LOCAL_EPUB_DIR) or DefaultValue.CURRENT_DIR)
            / self.filepath
        )

        # ---------------------------------------------------------
        # Missing EPUB
        #
        # Reading metadata would raise FileNotFoundError, which the
        # runner treats as a per-novel failure and skips entirely --
        # including the epub_exists update. Record the missing file
        # and stop here instead, so the rest of the sync can commit
        # epub_exists=False.
        # ---------------------------------------------------------

        if not epub_path.is_file():
            self.ctx.logger.warning(f"EPUB file not found: {epub_path}")
            self.data = {
                MetadataKey.EPUB_EXISTS: False,
                MetadataKey.FILEPATH: self.filepath,
            }
            self.ctx.logger.debug("Local provider loaded 2 fields (EPUB missing).")
            return

        # ---------------------------------------------------------
        # Basic EPUB metadata
        # ---------------------------------------------------------

        self.meta = get_epub_metadata(self.filepath)

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
            MetadataKey.FILEPATH: self.filepath,
            MetadataKey.EPUB_EXISTS: True,
        }

        self.ctx.logger.debug(f"Local provider loaded {len(self.data)} fields.")

    def fetch_cover(self, overwrite=False):
        """
        Fetch the cover image from the EPUB.
        """

        self.ctx.logger.info("Fetching local cover...")
        self.ctx.emit(Event.ASSET, asset=Asset.COVER)

        cover = extract_epub_cover(self.filepath, overwrite=overwrite)

        if cover:
            self.ctx.logger.info(f"Cover ready: {cover}")
        else:
            self.ctx.logger.warning("Cover extraction failed.")

        return cover

    def get_progress(self):
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
        return progress.chapter if progress else None


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

        if self.source != SourceDomain.WEBNOVEL:
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
            MetadataKey.SOURCE: SourceDomain.WEBNOVEL,
            MetadataKey.ONLINE_CHAPTERS: info.chapter,
            MetadataKey.LATEST_CHAPTER_TIME: info.chapter_time,
            MetadataKey.ONLINE_CHARACTERS: _client.count_online_characters(book_id),
            MetadataKey.STATUS: info.status,
            MetadataKey.COVER: info.cover,
            MetadataKey.FILEPATH: self.filepath,
        }

        self.ctx.logger.debug(f"Online provider loaded {len(self.data)} fields.")

    def fetch_cover(self, overwrite=False):
        """
        Fetch the cover image from the online source.
        """

        self.ctx.logger.info("Fetching online cover...")
        self.ctx.emit(Event.ASSET, asset=Asset.COVER)
        cover = _client.fetch_cover_image(self.book_id, overwrite=overwrite)

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

        output_dir = (
            Path(db.get_value(SettingKey.LOCAL_EPUB_DIR) or DefaultValue.CURRENT_DIR)
            / self.filepath
        )
        self.ctx.emit(Event.ASSET, asset=Asset.CHARACTERS)
        result = WN_fetch_characters(book_id=self.book_id, output_dir=output_dir)

        self.ctx.logger.info(
            f"Characters: {result['characters']} "
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
