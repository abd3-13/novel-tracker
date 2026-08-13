from app.constants import Event, MetadataKey, Provider, Stage

from .collector import SyncCollector
from .context import SyncContext
from .logger import SyncLogger
from .metadata import FIELDS
from .providers import (
    LocalProvider,
    OnlineProvider,
    ProviderManager,
)


class SyncEngine:
    """
    Executes synchronization jobs.

    Responsibilities:

    - Create synchronization context
    - Initialize providers
    - Execute metadata synchronization
    - Commit database updates

    Business logic belongs in metadata.py,
    not in the engine.
    """

    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, job, novel):
        """
        Execute a synchronization job for a single novel.
        """

        ctx = self._create_context(job, novel)

        ctx.logger.job(job.profile)

        self._register_providers(ctx)

        ctx.emit(Event.STAGE, stage=Stage.PROVIDERS)

        self._load_providers(ctx)
        ctx.emit(Event.STAGE, stage=Stage.METADATA)

        self._sync_fields(ctx)
        ctx.emit(Event.STAGE, stage=Stage.COMMIT)

        self._commit(ctx)
        ctx.emit(Event.STAGE, stage=Stage.DONE)

        return ctx.result or {
            "id": ctx.novel[MetadataKey.ID],
            "updated": False,
            "changes": {},
        }

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def _create_context(self, job, novel):
        """
        Create the runtime synchronization context.
        """

        ctx = SyncContext(job, novel)

        ctx.logger = SyncLogger(level=job.log_level)

        ctx.collector = SyncCollector()

        ctx.providers = ProviderManager()

        return ctx

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    def _register_providers(self, ctx):
        """
        Register available metadata providers.
        """

        ctx.providers.register(Provider.LOCAL, LocalProvider(ctx))

        ctx.providers.register(Provider.ONLINE, OnlineProvider(ctx))

    def _load_providers(self, ctx):
        """
        Load only the providers required for this job.
        """

        match ctx.job.source:
            case Provider.LOCAL:
                ctx.providers.load(Provider.LOCAL)

            case Provider.ONLINE:
                ctx.providers.load(Provider.ONLINE)

            case _:
                raise ValueError(f"Unknown sync source: {ctx.job.source}")

    # ------------------------------------------------------------------
    # Synchronization
    # ------------------------------------------------------------------

    def _sync_fields(self, ctx):
        """
        Synchronize all requested metadata fields.
        """

        for field_name in ctx.job.fields:
            field = FIELDS.get(field_name)

            if field is None:
                continue

            if not field.enabled:
                continue

            if field.synchronizer is None:
                continue

            field.synchronizer(ctx, field)

    # ------------------------------------------------------------------
    # Commit
    # ------------------------------------------------------------------

    def _commit(self, ctx):
        """
        Commit updates to the database.
        """

        updates = ctx.collector.as_dict()

        ctx.logger.collector(updates)

        if updates:
            if ctx.job.dry_run:
                ctx.logger.info("Dry run - skipping database update")
            else:
                self.db.update_novel(
                    ctx.novel[MetadataKey.ID], updates, table=ctx.job.table
                )

        else:
            ctx.logger.info("No updates to commit.")

        ctx.result = {
            "id": ctx.novel[MetadataKey.ID],
            "title": ctx.novel[MetadataKey.TITLE],
            "updated": bool(updates),
            "changes": updates,
            "errors": list(ctx.logger.errors),
            "warnings": list(ctx.logger.warnings),
        }
