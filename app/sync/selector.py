from dataclasses import dataclass

from app.constants import DatabaseColumn, Default
from app.utils import db


@dataclass(slots=True)
class BulkSelector:
    """
    Select novels for synchronization.

    Responsible only for retrieving novels from the database.
    """

    table: str = Default.NOVEL_TABLE

    # ------------------------------------------------------------------
    # Base Query
    # ------------------------------------------------------------------

    @property
    def _select(self) -> str:
        return f"SELECT * FROM {self.table}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fetch(self, query: str, params=()) -> list[dict]:
        """
        Execute a query and return rows as dictionaries.
        """

        rows, cur, conn = db.fetch_all(query, params)

        columns = [column[0] for column in cur.description]

        result = [dict(zip(columns, row)) for row in rows]

        conn.close()

        return result

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def all(self) -> list[dict]:
        """
        Select every novel.
        """

        return self._fetch(self._select)

    def ids(self, ids: list[int]) -> list[dict]:
        """
        Select novels by ID.
        """

        if not ids:
            return []

        placeholders = ",".join("?" * len(ids))

        return self._fetch(
            f"{self._select} WHERE {DatabaseColumn.ID} IN ({placeholders})", tuple(ids)
        )

    def column(self, column: str, value) -> list[dict]:
        """
        Select novels where a column matches a value.
        """

        return self._fetch(f"{self._select} WHERE {column} = ?", (value,))

    def where(self, where: str, params=()) -> list[dict]:
        """
        Select novels using a custom WHERE clause.

        Example:
            selector.where(f"{DatabaseColumn.ONLINE_CHAPTERS} > {DatabaseColumn.LOCAL_CHAPTERS}")
        """

        return self._fetch(f"{self._select} WHERE {where}", params)
