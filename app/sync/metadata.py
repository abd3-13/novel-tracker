from dataclasses import dataclass, field
from typing import Any, Callable

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

    new_value = ctx.providers.get_value(
        ctx.job.source,
        field,
    )

    current_value = ctx.novel.get(
        field.column,
    )

    if not SyncStrategy.should_update(
        ctx.job.mode,
        current_value,
        new_value,
    ):
        return

    ctx.collector.set(
        field.column,
        new_value,
    )


# =============================================================================
# Special Synchronizers
# =============================================================================


def sync_cover(ctx, field: MetadataField):
    """
    Synchronize cover image.

    Currently behaves the same as the generic synchronizer.
    A future version may implement online->local fallback logic.
    """
    generic_sync(ctx, field)


def sync_status(ctx, field: MetadataField):
    """
    Synchronize novel status.
    """
    generic_sync(ctx, field)


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
    "title": MetadataField(
        column="name",
        name="Title",
        sources={
            "local": "title",
            "online": "title",
        },
        synchronizer=generic_sync,
    ),
    "url": MetadataField(
        column="url",
        name="URL",
        sources={
            "local": "url",
        },
        synchronizer=generic_sync,
    ),
    "author": MetadataField(
        column="author",
        name="Author",
        sources={
            "local": "author",
            "online": "author",
        },
        synchronizer=generic_sync,
    ),
    "description": MetadataField(
        column="description",
        name="Description",
        sources={
            "local": "description",
            "online": "description",
        },
        synchronizer=generic_sync,
    ),
    "source": MetadataField(
        column="source",
        name="Source",
        sources={
            "local": "source",
        },
        synchronizer=generic_sync,
    ),
    # -----------------------------------------------------------------
    # Chapters
    # -----------------------------------------------------------------
    "localchap": MetadataField(
        column="localchap",
        name="Local Chapters",
        sources={
            "local": "localchap",
        },
        synchronizer=generic_sync,
    ),
    "onlinechap": MetadataField(
        column="onlinechap",
        name="Online Chapters",
        sources={
            "online": "onlinechap",
        },
        synchronizer=generic_sync,
    ),
    "latestchaptime": MetadataField(
        column="latestchaptime",
        name="Latest Chapter Time",
        sources={
            "online": "latestchaptime",
        },
        synchronizer=generic_sync,
    ),
    "local_lastchaptitle": MetadataField(
        column="local_lastchaptitle",
        name="Last Chapter Title",
        sources={
            "local": "local_lastchaptitle",
        },
        synchronizer=generic_sync,
    ),
    "local_lastchapfile": MetadataField(
        column="local_lastchapfile",
        name="Last Chapter File",
        sources={
            "local": "local_lastchapfile",
        },
        synchronizer=generic_sync,
    ),
    # -----------------------------------------------------------------
    # Cover
    # -----------------------------------------------------------------
    "cover": MetadataField(
        column="cover_path",
        name="Cover",
        sources={
            "local": "cover",
            "online": "cover",
        },
        synchronizer=sync_cover,
    ),
    # -----------------------------------------------------------------
    # Characters
    # -----------------------------------------------------------------
    "characters": MetadataField(
        column="characters",
        name="Characters",
        sources={
            "local": "characters",
        },
        synchronizer=generic_sync,
    ),
    "online_characters": MetadataField(
        column="online_characters",
        name="Online Characters",
        sources={
            "online": "online_characters",
        },
        synchronizer=generic_sync,
    ),
    # -----------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------
    "status": MetadataField(
        column="status",
        name="Status",
        sources={
            "online": "status",
        },
        synchronizer=sync_status,
    ),
    # -----------------------------------------------------------------
    # Progress
    # -----------------------------------------------------------------
    "progress": MetadataField(
        column="progress",
        name="Reading Progress",
        sources={
            "local": "progress",
        },
        synchronizer=sync_progress,
    ),
    "progress_updated": MetadataField(
        column="progress_updated",
        name="Progress Updated",
        sources={
            "local": "progress_updated",
        },
        synchronizer=generic_sync,
    ),
    # -----------------------------------------------------------------
    # File
    # -----------------------------------------------------------------
    "filepath": MetadataField(
        column="filepath",
        name="EPUB File",
        sources={
            "local": "filepath",
        },
        synchronizer=generic_sync,
    ),
    "epub_exists": MetadataField(
        column="epub_exists",
        name="EPUB Exists",
        sources={
            "local": "epub_exists",
        },
        synchronizer=generic_sync,
    ),
}
