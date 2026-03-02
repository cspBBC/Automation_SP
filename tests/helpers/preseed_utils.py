import os
import pyodbc
from core.db.connection import get_connection


def _read_sql(path: str) -> str:
    """Read a SQL file and return its contents."""
    with open(path, "r", encoding="utf8") as f:
        return f.read()


def verify_preseed_exists(module_path: str, filename: str) -> None:
    """Execute each query in the given file and assert it returns rows.

    The file should contain one or more SELECT statements that check for the
    presence of required rows.  No inserts or updates should be performed.
    If any query returns zero rows an AssertionError is raised, indicating
    that the test's preconditions are not met.
    """
    full = os.path.join(os.path.dirname(str(module_path)), filename)
    if not os.path.isfile(full):
        # nothing to verify
        return

    sql = _read_sql(full)
    # split on semicolon but ignore empty fragments
    statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
    if not statements:
        return

    with get_connection() as conn:
        cur = conn.cursor()
        for stmt in statements:
            cur.execute(stmt)
            rows = cur.fetchall()
            if not rows:
                raise AssertionError(
                    f"Precondition failed: '{filename}' query returned no rows:\n{stmt}"
                )
