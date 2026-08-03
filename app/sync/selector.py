from dataclasses import dataclass

from app.utils import db


@dataclass(slots=True)
class BulkSelector:
    """
    Select novels for synchronization.

    This class is responsible only for retrieving novels
    from the database.

    It performs no synchronization logic.
    """

    table: str = "novels"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fetch(self, query: str, params=()):
        """
        Execute a query and return novels as dictionaries.
        """

        rows, cur, conn = db.fetch_all(query, params)

        columns = [c[0] for c in cur.description]

        novels = [dict(zip(columns, row)) for row in rows]

        conn.close()

        return novels

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def all(self):
        """
        Select every novel.
        """

        return self._fetch(f"SELECT * FROM {self.table}")

    def ids(self, ids):
        """
        Select novels by ID.
        """

        if not ids:
            return []

        placeholders = ",".join("?" * len(ids))

        return self._fetch(
            f"""
            SELECT *
            FROM {self.table}
            WHERE id IN ({placeholders})
            """,
            tuple(ids),
        )

    def source(self, source):
        """
        Select novels by source.
        """

        return self._fetch(
            f"""
            SELECT *
            FROM {self.table}
            WHERE source = ?
            """,
            (source,),
        )

    def status(self, status):
        """
        Select novels by status.
        """

        return self._fetch(
            f"""
            SELECT *
            FROM {self.table}
            WHERE status = ?
            """,
            (status,),
        )

    def where(self, where, params=()):
        """
        Select novels using a custom WHERE clause.

        Example:
            selector.where(
                "onlinechap > localchap"
            )
        """

        return self._fetch(
            f"""
            SELECT *
            FROM {self.table}
            WHERE {where}
            """,
            params,
        )
