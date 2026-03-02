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
        module_path: Module path (for logging/reference, not used for file path)
        filename: SQL filename to execute from data_layer/preseed_data/
        
    Raises:
        AssertionError: If any query returns zero rows
    """
    # Look for preseed SQL files in data_layer/preseed_data/
    import pathlib
    project_root = pathlib.Path(__file__).parent.parent
    full = project_root / "data_layer" / "preseed_data" / filename
    
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
