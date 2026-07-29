from .collector import SyncCollector
from .context import SyncContext
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

        self._register_providers(ctx)

        self._load_providers(ctx)

        self._sync_fields(ctx)

        self._commit(ctx)

        return ctx.result

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def _create_context(self, job, novel):
        """
        Create the runtime synchronization context.
        """

        ctx = SyncContext(job, novel)

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

        ctx.providers.register(
            "local",
            LocalProvider(ctx),
        )

        ctx.providers.register(
            "online",
            OnlineProvider(ctx),
        )

    def _load_providers(self, ctx):
        """
        Load metadata from all providers.
        """

        ctx.providers.load_all()

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
    # Database
    # ------------------------------------------------------------------
    #    def _commit(self, ctx):
    #        """
    #        Persist collected updates.
    #        """
    #
    #        updates = ctx.collector.as_dict()
    #
    #        if not updates:
    #            ctx.result = {
    #                "id": ctx.novel["id"],
    #                "updated": False,
    #                "changes": {},
    #            }
    #            return
    #
    #        self.db.update_novel(
    #            ctx.novel["id"],
    #            updates,
    #        )
    #
    #        ctx.result = {
    #            "id": ctx.novel["id"],
    #            "updated": True,
    #            "changes": updates,
    #        }
    #
    def _commit(self, ctx):

        updates = ctx.collector.as_dict()

        print("\n===== SyncCollector =====")

        if not updates:
            print("No updates.")
        else:
            for k, v in updates.items():
                print(f"{k:25} : {v}")

        if updates:
            self.db.update_novel(ctx.novel["id"], updates, table=ctx.job.table)

        ctx.result = updates
