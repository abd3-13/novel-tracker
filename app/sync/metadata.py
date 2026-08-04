from dataclasses import dataclass, field
from typing import Any, Callable  # noqa: UP035

from app.constants import DatabaseColumn, Event, MetadataKey, Provider, SyncAction

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

    # Display name
    name: str

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

    # Allow disabling fields without removing them
    enabled: bool = True


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
    cover_id = provider.fetch_cover()
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
        name="Title",
        sources={
            Provider.LOCAL: MetadataKey.TITLE,
            Provider.ONLINE: MetadataKey.TITLE,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.URL: MetadataField(
        column=DatabaseColumn.URL,
        name="URL",
        sources={
            Provider.LOCAL: MetadataKey.URL,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.AUTHOR: MetadataField(
        column=DatabaseColumn.AUTHOR,
        name="Author",
        sources={
            Provider.LOCAL: MetadataKey.AUTHOR,
            Provider.ONLINE: MetadataKey.AUTHOR,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.DESCRIPTION: MetadataField(
        column=DatabaseColumn.DESCRIPTION,
        name="Description",
        sources={
            Provider.LOCAL: MetadataKey.DESCRIPTION,
            Provider.ONLINE: MetadataKey.DESCRIPTION,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.SOURCE: MetadataField(
        column=DatabaseColumn.SOURCE,
        name="Source",
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
        name="Local Chapters",
        sources={
            Provider.LOCAL: MetadataKey.LOCAL_CHAPTERS,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.ONLINE_CHAPTERS: MetadataField(
        column=DatabaseColumn.ONLINE_CHAPTERS,
        name="Online Chapters",
        sources={
            Provider.ONLINE: MetadataKey.ONLINE_CHAPTERS,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.LATEST_CHAPTER_TIME: MetadataField(
        column=DatabaseColumn.LATEST_CHAPTER_TIME,
        name="Latest Chapter Time",
        sources={
            Provider.ONLINE: MetadataKey.LATEST_CHAPTER_TIME,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.LOCAL_LAST_TITLE: MetadataField(
        column=DatabaseColumn.LOCAL_LAST_TITLE,
        name="Last Chapter Title",
        sources={
            Provider.LOCAL: MetadataKey.LOCAL_LAST_TITLE,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.LOCAL_LAST_FILE: MetadataField(
        column=DatabaseColumn.LOCAL_LAST_FILE,
        name="Last Chapter File",
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
        name="Cover",
        sources={
            Provider.LOCAL: MetadataKey.COVER,
        },
        synchronizer=generic_sync,
    ),
    SyncAction.FETCH_COVER: MetadataField(
        column=DatabaseColumn.COVER,
        name="Fetch Cover",
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
        name="Characters",
        sources={
            Provider.LOCAL: MetadataKey.CHARACTERS,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.ONLINE_CHARACTERS: MetadataField(
        column=DatabaseColumn.ONLINE_CHARACTERS,
        name="Online Characters",
        sources={
            Provider.ONLINE: MetadataKey.ONLINE_CHARACTERS,
        },
        synchronizer=generic_sync,
    ),
    SyncAction.FETCH_CHARACTERS: MetadataField(
        column=DatabaseColumn.CHARACTERS,
        name="Fetch Characters",
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
        name="Status",
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
        name="Reading Progress",
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
        name="EPUB File",
        sources={
            Provider.LOCAL: MetadataKey.FILEPATH,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.EPUB_EXISTS: MetadataField(
        column=DatabaseColumn.EPUB_EXISTS,
        name="EPUB Exists",
        sources={
            Provider.LOCAL: MetadataKey.EPUB_EXISTS,
        },
        synchronizer=generic_sync,
    ),
}
