"""Preseed Validator - Validates test preconditions."""

import os
import logging
from database_layer.connection import get_connection

logger = logging.getLogger(__name__)


def _read_sql(path: str) -> str:
    """Read a SQL file and return its contents."""
    with open(path, "r", encoding="utf8") as f:
        return f.read()


def verify_preseed_exists(module_path: str, filename: str) -> None:
    """Execute each query in the given file and assert it returns rows.
    
    Args:
        module_path: Module path for file location
        filename: SQL filename to execute
        
    Raises:
        AssertionError: If any query returns zero rows
    """
    full = os.path.join(os.path.dirname(str(module_path)), filename)
    if not os.path.isfile(full):
        return

    sql = _read_sql(full)
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
