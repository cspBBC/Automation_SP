"""Preseed Validator - Validates test preconditions."""

import os
import logging
from database_layer.connection import get_connection

logger = logging.getLogger('sp_validation')


def _read_sql(path: str) -> str:
    """Read a SQL file and return its contents."""
    with open(path, "r", encoding="utf8") as f:
        return f.read()


def verify_preseed_exists(module_path: str, filename: str) -> None:
    """Execute each query in the given file and assert it returns rows.
    
    Args:
        module_path: Module name (e.g., 'usp_CreateUpdateSchedulingTeam')
        filename: SQL filename to execute from preseed location
        
    Raises:
        AssertionError: If any query returns zero rows
        
    Preseed file structure (auto-detected):
        New: data_layer/test_data/{module}/preseed_data/{filename}
        Legacy: data_layer/preseed_data/{filename}
    """
    # Look for preseed SQL files in modularized or legacy locations
    import pathlib
    project_root = pathlib.Path(__file__).parent.parent
    
    # Try new modularized structure first
    candidate_paths = [
        project_root / "data_layer" / "test_data" / module_path / "preseed_data" / filename,
        project_root / "data_layer" / "preseed_data" / filename,  # Legacy fallback
    ]
    
    full = None
    for path in candidate_paths:
        if os.path.isfile(path):
            full = path
            break
    
    if not full:
        logger.info(f"Preseed Reference File: {os.path.abspath(candidate_paths[0])}")
        logger.info(f"File exists: False (skipping)")
        return

    logger.info(f"Preseed Reference File: {os.path.abspath(full)}")
    logger.info(f"File exists: True")
    logger.info(f"File size: {os.path.getsize(full)} bytes")

    sql = _read_sql(full)
    statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
    if not statements:
        return

    logger.info(f"Executing {len(statements)} statement(s) from {filename}...")
    
    with get_connection() as conn:
        cur = conn.cursor()
        for stmt_idx, stmt in enumerate(statements, 1):
            logger.info(f"  Preseed statement {stmt_idx}/{len(statements)}: {stmt[:80]}...")
            cur.execute(stmt)
            rows = cur.fetchall()
            if not rows:
                raise AssertionError(
                    f"Precondition failed: '{filename}' query returned no rows:\n{stmt}"
                )
            logger.info(f"  [OK] Returned {len(rows)} row(s)")
