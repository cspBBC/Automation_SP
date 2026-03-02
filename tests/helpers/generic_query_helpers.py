from core.db.connection import DBSession
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GENERIC QUERY/VALIDATION FUNCTIONS
# ---------------------------------------------------------------------------

def execute_query(sql: str, params: List = None) -> List[Dict[str, Any]]:
    """Run a parametrized SELECT statement and return list of row dicts.

    This is the most primitive helper; higher-level functions can build SQL
    strings and then pass them here.  Having a single executor makes it easy
    to centralise logging, error handling, or debugging output.

    Args:
        sql: SQL string with ``?`` placeholders for parameters.
        params: sequence of parameter values.

    Returns:
        A list of dictionaries where each key is a column name.  An empty list
        is returned when no rows are found.
    """
    params = params or []
    with DBSession() as db:
        db.cursor.execute(sql, params)
        cols = [d[0] for d in db.cursor.description] if db.cursor.description else []
        rows = db.cursor.fetchall()
        return [{cols[i]: row[i] for i in range(len(cols))} for row in rows]


def execute_statement(sql: str, params: List = None) -> int:
    """Execute a DML statement (DELETE, UPDATE, INSERT) and return affected row count.

    Unlike execute_query, this does not attempt to fetch results.
    Safe for any non-SELECT statement.

    Args:
        sql: SQL string (DELETE, UPDATE, INSERT)
        params: parameter values (not used if SQL has no placeholders)

    Returns:
        Number of rows affected by the operation
    """
    params = params or []
    with DBSession() as db:
        db.cursor.execute(sql, params)
        return db.cursor.rowcount


def get_entity_details(table_name: str, id_column: str, entity_id: int) -> Dict[str, Any]:
    """Fetch a single row from any table by primary key.

    Delegates to :func:`execute_query` using a simple SELECT statement.
    """
    sql = f"SELECT * FROM {table_name} WHERE {id_column} = ?"
    results = execute_query(sql, [entity_id])
    return results[0] if results else {}


def query_table(table_name: str, where_clause: str = "", params: List = None) -> List[Dict[str, Any]]:
    """Run a SELECT * against any table with an optional WHERE clause.

    ``where_clause`` should **not** contain the leading ``WHERE`` keyword.

    Args:
        table_name: table to query
        where_clause: SQL conditions (e.g. ``"isActive = ?"``)
        params: parameter values

    Returns:
        List of row-dictionaries; may be empty.
    """
    params = params or []
    sql = f"SELECT * FROM {table_name}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    with DBSession() as db:
        db.cursor.execute(sql, params)
        cols = [d[0] for d in db.cursor.description] if db.cursor.description else []
        rows = db.cursor.fetchall()
        return [{cols[i]: row[i] for i in range(len(cols))} for row in rows]


def validate_entity_exists(table_name: str, id_column: str, entity_id: int) -> bool:
    """Return ``True`` if a row with the given id exists in the table."""
    sql = f"SELECT COUNT(1) FROM {table_name} WHERE {id_column} = ?"
    with DBSession() as db:
        db.cursor.execute(sql, [entity_id])
        row = db.cursor.fetchone()
        if row:
            count = row[0] if isinstance(row, (tuple, list)) else row.get('cnt', 0)
            return count > 0
    return False


def validate_entity_attribute(table_name: str,
                              id_column: str,
                              entity_id: int,
                              attribute_column: str,
                              expected_value: Any) -> bool:
    """Ensure that the given column on the row matches ``expected_value``."""
    sql = f"SELECT {attribute_column} FROM {table_name} WHERE {id_column} = ?"
    with DBSession() as db:
        db.cursor.execute(sql, [entity_id])
        row = db.cursor.fetchone()
        if row:
            actual = row[0] if isinstance(row, (tuple, list)) else row.get(attribute_column)
            return actual == expected_value
    return False
