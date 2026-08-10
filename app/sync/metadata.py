from dataclasses import dataclass, field
from typing import Any, Callable  # noqa: UP035

from app.constants import (
    DatabaseColumn,
    Event,
    MetadataKey,
    Provider,
    SyncAction,
    SyncMode,
)

from .strategy import SyncStrategy

# =============================================================================
# Metadata Field
# =============================================================================


@dataclass(slots=True)
class MetadataField:
    """
    Describes how a metadata field is synchronized.
    """

    # Database column
    column: str
    group: str

    name: str
    description: str = ""
    icon: str = "database"

    # Provider key mapping
    #
    # Example:
    # {
    #     "local": "author",
    #     "online": "author",
    # }
    sources: dict[str, str] = field(default_factory=dict)

    # Synchronization function
    synchronizer: Callable[..., Any] | None = None

    visible: bool = True
    default: bool = True

    order: int = 0

    # Allow disabling fields without removing them
    enabled: bool = True

    def to_ui(self):
        return {
            "id": self.column,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "default": self.default,
            "providers": [p for p in self.sources],
        }


# =============================================================================
# Generic Synchronizer
# =============================================================================


def generic_sync(ctx, field: MetadataField):
    """
    Generic synchronizer used by most metadata fields.
    """

    new_value = ctx.providers.get_value(ctx.job.source, field)

    current_value = ctx.novel.get(field.column)

    should_update = SyncStrategy.should_update(ctx.job.mode, current_value, new_value)

    ctx.logger.field(field.column, current_value, new_value, should_update)
    ctx.emit(Event.FIELD, field=field.column)

    # ----------------------------
    # Sync
    # ----------------------------

    if not should_update:
        return

    ctx.collector.set(field.column, new_value)

    ctx.logger.debug(f"Queued update: {field.column}")


# =============================================================================
# Special Synchronizers
# =============================================================================


def sync_cover_asset(ctx, field: MetadataField):
    """
    Synchronize cover image.
    """
    provider = ctx.providers.get_provider(ctx.job.source)
    overwrite = ctx.job.mode == SyncMode.OVERWRITE
    cover_id = provider.fetch_cover(overwrite=overwrite)
    if cover_id:
        ctx.collector.set(field.column, cover_id)


def sync_character_assets(ctx, field: MetadataField):
    """
    Synchronize character assets.
    """
    provider = ctx.providers.get_provider(ctx.job.source)
    provider.fetch_characters()


# TODO: Implement a separate synchronizer for progress, currently using the local provider
def sync_progress(ctx, field: MetadataField):
    """
    Synchronize MoonReader progress.
    """
    generic_sync(ctx, field)


# =============================================================================
# Metadata Registry
# =============================================================================

FIELDS = {
    # -----------------------------------------------------------------
    # Basic
    # -----------------------------------------------------------------
    MetadataKey.TITLE: MetadataField(
        column=DatabaseColumn.TITLE,
        group="Basic",
        name="Title",
        description="Novel title.",
        icon="book",
        order=10,
        sources={
            Provider.LOCAL: MetadataKey.TITLE,
            Provider.ONLINE: MetadataKey.TITLE,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.URL: MetadataField(
        column=DatabaseColumn.URL,
        group="Basic",
        name="URL",
        description="Original novel website address.",
        icon="link",
        order=20,
        sources={
            Provider.LOCAL: MetadataKey.URL,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.AUTHOR: MetadataField(
        column=DatabaseColumn.AUTHOR,
        group="Basic",
        name="Author",
        description="Novel author.",
        icon="user",
        order=30,
        sources={
            Provider.LOCAL: MetadataKey.AUTHOR,
            Provider.ONLINE: MetadataKey.AUTHOR,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.DESCRIPTION: MetadataField(
        column=DatabaseColumn.DESCRIPTION,
        group="Basic",
        name="Description",
        description="Synopsis or summary.",
        icon="align-left",
        order=40,
        sources={
            Provider.LOCAL: MetadataKey.DESCRIPTION,
            Provider.ONLINE: MetadataKey.DESCRIPTION,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.SOURCE: MetadataField(
        column=DatabaseColumn.SOURCE,
        group="Basic",
        name="Source",
        description="Metadata provider or website.",
        icon="world",
        order=50,
        sources={
            Provider.LOCAL: MetadataKey.SOURCE,
        },
        synchronizer=generic_sync,
    ),
    # -----------------------------------------------------------------
    # Chapters
    # -----------------------------------------------------------------
    MetadataKey.LOCAL_CHAPTERS: MetadataField(
        column=DatabaseColumn.LOCAL_CHAPTERS,
        group="Chapters",
        name="Local Chapters",
        description="Number of chapters stored in the EPUB.",
        icon="books",
        order=100,
        sources={
            Provider.LOCAL: MetadataKey.LOCAL_CHAPTERS,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.ONLINE_CHAPTERS: MetadataField(
        column=DatabaseColumn.ONLINE_CHAPTERS,
        group="Chapters",
        name="Online Chapters",
        description="Latest chapter count available online.",
        icon="cloud",
        order=110,
        sources={
            Provider.ONLINE: MetadataKey.ONLINE_CHAPTERS,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.LATEST_CHAPTER_TIME: MetadataField(
        column=DatabaseColumn.LATEST_CHAPTER_TIME,
        group="Chapters",
        name="Latest Chapter Time",
        description="Publication time of the latest online chapter.",
        icon="clock",
        order=120,
        sources={
            Provider.ONLINE: MetadataKey.LATEST_CHAPTER_TIME,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.LOCAL_LAST_TITLE: MetadataField(
        column=DatabaseColumn.LOCAL_LAST_TITLE,
        group="Chapters",
        name="Last Chapter Title",
        description="Title of the last chapter in the EPUB.",
        icon="book-2",
        order=130,
        sources={
            Provider.LOCAL: MetadataKey.LOCAL_LAST_TITLE,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.LOCAL_LAST_FILE: MetadataField(
        column=DatabaseColumn.LOCAL_LAST_FILE,
        group="Chapters",
        name="Last Chapter File",
        description="Internal EPUB file for the last chapter.",
        icon="file-text",
        order=140,
        sources={
            Provider.LOCAL: MetadataKey.LOCAL_LAST_FILE,
        },
        synchronizer=generic_sync,
    ),
    # -----------------------------------------------------------------
    # Cover
    # -----------------------------------------------------------------
    MetadataKey.COVER: MetadataField(
        column=DatabaseColumn.COVER,
        group="Cover",
        name="Cover",
        description="Stored cover image.",
        icon="photo",
        order=200,
        sources={
            Provider.LOCAL: MetadataKey.COVER,
        },
        synchronizer=generic_sync,
    ),
    SyncAction.FETCH_COVER: MetadataField(
        column=SyncAction.FETCH_COVER,
        group="Cover",
        name="Fetch Cover",
        description="Download a fresh cover image.",
        icon="download",
        order=210,
        sources={
            Provider.LOCAL: MetadataKey.COVER,
            Provider.ONLINE: MetadataKey.COVER,
        },
        synchronizer=sync_cover_asset,
    ),
    # -----------------------------------------------------------------
    # Characters
    # -----------------------------------------------------------------
    MetadataKey.CHARACTERS: MetadataField(
        column=DatabaseColumn.CHARACTERS,
        group="Characters",
        name="Characters",
        description="Stored character list.",
        icon="users",
        order=300,
        sources={
            Provider.LOCAL: MetadataKey.CHARACTERS,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.ONLINE_CHARACTERS: MetadataField(
        column=DatabaseColumn.ONLINE_CHARACTERS,
        group="Characters",
        name="Online Characters",
        description="Characters available from the online provider.",
        icon="users-group",
        order=310,
        sources={
            Provider.ONLINE: MetadataKey.ONLINE_CHARACTERS,
        },
        synchronizer=generic_sync,
    ),
    SyncAction.FETCH_CHARACTERS: MetadataField(
        column=SyncAction.FETCH_CHARACTERS,
        group="Characters",
        name="Fetch Characters",
        description="Download character images and metadata.",
        icon="user-down",
        order=320,
        sources={
            Provider.ONLINE: MetadataKey.ONLINE_CHARACTERS,
        },
        synchronizer=sync_character_assets,
    ),
    # -----------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------
    MetadataKey.STATUS: MetadataField(
        column=DatabaseColumn.STATUS,
        group="Status",
        name="Status",
        description="Publication status of the novel.",
        icon="circle-check",
        order=400,
        sources={
            Provider.ONLINE: MetadataKey.STATUS,
        },
        synchronizer=generic_sync,
    ),
    # -----------------------------------------------------------------
    # Progress
    # -----------------------------------------------------------------
    MetadataKey.PROGRESS: MetadataField(
        column=DatabaseColumn.PROGRESS,
        group="Status",
        name="Reading Progress",
        description="Reading progress imported from Moon+ Reader.",
        icon="progress",
        order=500,
        sources={
            Provider.LOCAL: MetadataKey.PROGRESS,
        },
        synchronizer=sync_progress,
    ),
    # -----------------------------------------------------------------
    # File
    # -----------------------------------------------------------------
    MetadataKey.FILEPATH: MetadataField(
        column=DatabaseColumn.FILEPATH,
        group="File",
        name="EPUB File",
        description="Path to the EPUB file.",
        icon="file",
        order=600,
        sources={
            Provider.LOCAL: MetadataKey.FILEPATH,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.EPUB_EXISTS: MetadataField(
        column=DatabaseColumn.EPUB_EXISTS,
        group="File",
        name="EPUB Exists",
        description="Whether the EPUB file exists on disk.",
        icon="file-check",
        order=610,
        sources={
            Provider.LOCAL: MetadataKey.EPUB_EXISTS,
        },
        synchronizer=generic_sync,
    ),
}
