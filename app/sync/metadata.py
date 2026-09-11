from dataclasses import dataclass, field
from typing import Any, Callable  # noqa: UP035

from app.constants import (
    DatabaseColumn,
    Event,
    MetadataDescription,
    MetadataGroup,
    MetadataIcon,
    MetadataKey,
    MetadataLabel,
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
    ctx.emit(
        Event.FIELD,
        field=field.column,
        name=field.name,
        value=new_value,
        should_update=should_update,
    )

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
    ctx.emit(Event.ASSET, asset=SyncAction.FETCH_COVER, name=field.name)
    provider = ctx.providers.get_provider(ctx.job.source)
    overwrite = ctx.job.mode == SyncMode.OVERWRITE
    cover_id = provider.fetch_cover(overwrite=overwrite)
    if cover_id:
        ctx.collector.set(field.column, cover_id)

    ctx.emit(Event.FIELD, field=field.column, name=field.name, value=cover_id)


def sync_character_assets(ctx, field: MetadataField):
    """
    Synchronize character assets.
    """
    ctx.emit(Event.ASSET, asset=SyncAction.FETCH_CHARACTERS, name=field.name)
    provider = ctx.providers.get_provider(ctx.job.source)
    provider.fetch_characters()


def sync_progress(ctx, field: MetadataField):
    """
    Synchronize MoonReader progress.
    """
    # generic_sync(ctx, field)

    provider = ctx.providers.get_provider(ctx.job.source)

    new_value = provider.get_progress()

    current_value = ctx.novel.get(field.column)

    should_update = SyncStrategy.should_update(ctx.job.mode, current_value, new_value)

    ctx.logger.field(field.column, current_value, new_value, should_update)
    ctx.emit(Event.FIELD, field=field.column, name=field.name, value=new_value)
    print(f"Progress: {current_value} -> {new_value} (should_update={should_update})")
    # ----------------------------
    # Sync
    # ----------------------------

    if not should_update:
        return

    ctx.collector.set(field.column, new_value)

    ctx.logger.debug(f"Queued update: {field.column}")


# =============================================================================
# Metadata Registry
# =============================================================================

FIELDS = {
    # -----------------------------------------------------------------
    # Basic
    # -----------------------------------------------------------------
    MetadataKey.TITLE: MetadataField(
        column=DatabaseColumn.TITLE,
        group=MetadataGroup.BASIC,
        name=MetadataLabel.TITLE,
        description=MetadataDescription.TITLE,
        icon=MetadataIcon.BOOK,
        order=10,
        sources={
            Provider.LOCAL: MetadataKey.TITLE,
            Provider.ONLINE: MetadataKey.TITLE,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.URL: MetadataField(
        column=DatabaseColumn.URL,
        group=MetadataGroup.BASIC,
        name=MetadataLabel.URL,
        description=MetadataDescription.URL,
        icon=MetadataIcon.LINK,
        order=20,
        sources={
            Provider.LOCAL: MetadataKey.URL,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.AUTHOR: MetadataField(
        column=DatabaseColumn.AUTHOR,
        group=MetadataGroup.BASIC,
        name=MetadataLabel.AUTHOR,
        description=MetadataDescription.AUTHOR,
        icon=MetadataIcon.USER,
        order=30,
        sources={
            Provider.LOCAL: MetadataKey.AUTHOR,
            Provider.ONLINE: MetadataKey.AUTHOR,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.DESCRIPTION: MetadataField(
        column=DatabaseColumn.DESCRIPTION,
        group=MetadataGroup.BASIC,
        name=MetadataLabel.DESCRIPTION,
        description=MetadataDescription.DESCRIPTION,
        icon=MetadataIcon.ALIGN_LEFT,
        order=40,
        sources={
            Provider.LOCAL: MetadataKey.DESCRIPTION,
            Provider.ONLINE: MetadataKey.DESCRIPTION,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.SOURCE: MetadataField(
        column=DatabaseColumn.SOURCE,
        group=MetadataGroup.BASIC,
        name=MetadataLabel.SOURCE,
        description=MetadataDescription.SOURCE,
        icon=MetadataIcon.WORLD,
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
        group=MetadataGroup.CHAPTERS,
        name=MetadataLabel.LOCAL_CHAPTERS,
        description=MetadataDescription.LOCAL_CHAPTERS,
        icon=MetadataIcon.BOOKS,
        order=100,
        sources={
            Provider.LOCAL: MetadataKey.LOCAL_CHAPTERS,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.ONLINE_CHAPTERS: MetadataField(
        column=DatabaseColumn.ONLINE_CHAPTERS,
        group=MetadataGroup.CHAPTERS,
        name=MetadataLabel.ONLINE_CHAPTERS,
        description=MetadataDescription.ONLINE_CHAPTERS,
        icon=MetadataIcon.CLOUD,
        order=110,
        sources={
            Provider.ONLINE: MetadataKey.ONLINE_CHAPTERS,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.LATEST_CHAPTER_TIME: MetadataField(
        column=DatabaseColumn.LATEST_CHAPTER_TIME,
        group=MetadataGroup.CHAPTERS,
        name=MetadataLabel.LATEST_CHAPTER_TIME,
        description=MetadataDescription.LATEST_CHAPTER_TIME,
        icon=MetadataIcon.CLOCK,
        order=120,
        sources={
            Provider.ONLINE: MetadataKey.LATEST_CHAPTER_TIME,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.LOCAL_LAST_TITLE: MetadataField(
        column=DatabaseColumn.LOCAL_LAST_TITLE,
        group=MetadataGroup.CHAPTERS,
        name=MetadataLabel.LOCAL_LAST_TITLE,
        description=MetadataDescription.LOCAL_LAST_TITLE,
        icon=MetadataIcon.BOOK_2,
        order=130,
        sources={
            Provider.LOCAL: MetadataKey.LOCAL_LAST_TITLE,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.LOCAL_LAST_FILE: MetadataField(
        column=DatabaseColumn.LOCAL_LAST_FILE,
        group=MetadataGroup.CHAPTERS,
        name=MetadataLabel.LOCAL_LAST_FILE,
        description=MetadataDescription.LOCAL_LAST_FILE,
        icon=MetadataIcon.FILE_TEXT,
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
        group=MetadataGroup.COVER,
        name=MetadataLabel.COVER,
        description=MetadataDescription.COVER,
        icon=MetadataIcon.PHOTO,
        order=200,
        sources={
            Provider.LOCAL: MetadataKey.COVER,
        },
        synchronizer=generic_sync,
    ),
    SyncAction.FETCH_COVER: MetadataField(
        column=SyncAction.FETCH_COVER,
        group=MetadataGroup.COVER,
        name=MetadataLabel.FETCH_COVER,
        description=MetadataDescription.FETCH_COVER,
        icon=MetadataIcon.DOWNLOAD,
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
        group=MetadataGroup.CHARACTERS,
        name=MetadataLabel.CHARACTERS,
        description=MetadataDescription.CHARACTERS,
        icon=MetadataIcon.USERS,
        order=300,
        sources={
            Provider.LOCAL: MetadataKey.CHARACTERS,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.ONLINE_CHARACTERS: MetadataField(
        column=DatabaseColumn.ONLINE_CHARACTERS,
        group=MetadataGroup.CHARACTERS,
        name=MetadataLabel.ONLINE_CHARACTERS,
        description=MetadataDescription.ONLINE_CHARACTERS,
        icon=MetadataIcon.USERS_GROUP,
        order=310,
        sources={
            Provider.ONLINE: MetadataKey.ONLINE_CHARACTERS,
        },
        synchronizer=generic_sync,
    ),
    SyncAction.FETCH_CHARACTERS: MetadataField(
        column=SyncAction.FETCH_CHARACTERS,
        group=MetadataGroup.CHARACTERS,
        name=MetadataLabel.FETCH_CHARACTERS,
        description=MetadataDescription.FETCH_CHARACTERS,
        icon=MetadataIcon.USER_DOWN,
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
        group=MetadataGroup.STATUS,
        name=MetadataLabel.STATUS,
        description=MetadataDescription.STATUS,
        icon=MetadataIcon.CIRCLE_CHECK,
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
        group=MetadataGroup.STATUS,
        name=MetadataLabel.PROGRESS,
        description=MetadataDescription.PROGRESS,
        icon=MetadataIcon.PROGRESS,
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
        group=MetadataGroup.FILE,
        name=MetadataLabel.FILEPATH,
        description=MetadataDescription.FILEPATH,
        icon=MetadataIcon.FILE,
        order=600,
        sources={
            Provider.LOCAL: MetadataKey.FILEPATH,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.EPUB_EXISTS: MetadataField(
        column=DatabaseColumn.EPUB_EXISTS,
        group=MetadataGroup.FILE,
        name=MetadataLabel.EPUB_EXISTS,
        description=MetadataDescription.EPUB_EXISTS,
        icon=MetadataIcon.FILE_CHECK,
        order=610,
        sources={
            Provider.LOCAL: MetadataKey.EPUB_EXISTS,
        },
        synchronizer=generic_sync,
    ),
    MetadataKey.DISCORD_CHANNEL_URL: MetadataField(
        column=DatabaseColumn.DISCORD_CHANNEL_URL,
        group=MetadataGroup.BASIC,
        name=MetadataLabel.DISCORD_CHANNEL_URL,
        description=MetadataDescription.DISCORD_CHANNEL_URL,
        icon=MetadataIcon.DISCORD,
        order=620,
        sources={
            Provider.LOCAL: MetadataKey.DISCORD_CHANNEL_URL,
        },
        synchronizer=generic_sync,
    ),
}
