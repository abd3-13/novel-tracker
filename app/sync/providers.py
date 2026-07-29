from pathlib import Path
from typing import Any

import app.utils.db as db

from .services import (
    count_local_characters,
    extract_epub_cover,
    extract_local_chap,
    get_epub_metadata,
)

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
        pass

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

        epub_path = novel.get("filepath")

        if not epub_path:
            return

        # ---------------------------------------------------------
        # Basic EPUB metadata
        # ---------------------------------------------------------

        meta = get_epub_metadata(epub_path)

        chapters, last_title, last_file = extract_local_chap(epub_path)

        # ---------------------------------------------------------
        # Build provider data
        # ---------------------------------------------------------

        self.data = {
            # Basic
            "title": meta.get("title"),
            "author": meta.get("author"),
            "description": meta.get("description"),
            "url": meta.get("url"),
            "source": meta.get("source"),
            # Chapters
            "localchap": chapters,
            "local_lastchaptitle": last_title,
            "local_lastchapfile": last_file,
            # Characters
            "characters": count_local_characters(epub_path),
            # Cover
            "cover": extract_epub_cover(
                epub_path=epub_path,
                getfrom="local",
                meta=meta,
            ),
            # Progress
            "progress": None,
            "progress_updated": None,
            # File
            "filepath": epub_path,
            "epub_exists": (
                Path(db.get_value("LOCAL_EPUB_DIR") or "./") / epub_path
            ).exists(),
        }


# =============================================================================
# Online Provider
# =============================================================================


class OnlineProvider(BaseProvider):
    """
    Provides metadata from the online source.
    """

    def load(self) -> None:
        """
        Load online metadata.

        Implement later.
        """
        pass


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
        for provider in self._providers.values():
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

        if attribute is None:
            return None

        return provider.get(attribute)

    def get_value_from(self, source: str, field):
        """
        Explicitly fetch a value from a specific source.

        Alias for get_value(), intended for special metadata
        handlers such as cover synchronization.
        """
        return self.get_value(source, field)
