"""Test Case Builder - Builds test cases from data."""

from typing import Dict, Any, List
import datetime


def get_column_names(table_name: str) -> list:
    """Get column names for a table from INFORMATION_SCHEMA (cached).
    
    Returns list of column names in ordinal order.
    
    Args:
        table_name: Name of the table
        
    Returns:
        List of column names
    """
    # Module-level cache for table column names
    _column_cache = getattr(get_column_names, '_cache', {})
    if not hasattr(get_column_names, '_cache'):
        get_column_names._cache = _column_cache
    
    if table_name in _column_cache:
        return _column_cache[table_name]
    
    try:
        from database_layer.connection import DBSession
        with DBSession() as db:
            query = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
            """
            results = db.execute_query(query, [table_name])
            col_names = [row[0] for row in results] if results else []
            _column_cache[table_name] = col_names
            return col_names
    except Exception as e:
        return []


def build_test_context(params: Dict[str, Any], chain_data: Dict = None) -> Dict:
    """Build execution context with dynamic values.
    
    Args:
        params: Base parameters
        chain_data: Chain execution data to merge
        
    Returns:
        Context dictionary
    """
    ctx = {}
    
    # Add parameters to context
    if isinstance(params, dict):
        for k, v in params.items():
            name = k.lstrip('@')
            ctx[name] = v
    
    # Add chain data if present
    if chain_data:
        ctx.update(chain_data)
    
    # Add generated values if not present
    if 'generated_team_name' not in ctx:
        ctx['generated_team_name'] = f"AutoTest_{datetime.datetime.now():%Y%m%d%H%M%S}"
    
    return ctx
