"""Test Validator - Validates test results."""

from typing import Dict, List, Any, Tuple
from test_engine_layer.utils import Colors


def row_to_dict(row, col_names=None) -> Dict:
    """Convert a database row to dictionary.
    
    Args:
        row: pyodbc.Row or tuple
        col_names: Optional list of column names
        
    Returns:
        Dictionary representation of row
    """
    if isinstance(row, dict):
        return row
    
    if col_names:
        try:
            row_list = list(row)
            if len(col_names) == len(row_list):
                return dict(zip(col_names, row_list))
        except Exception:
            pass
    
    try:
        if hasattr(row, 'keys'):
            col_names_from_row = list(row.keys())
            result = {}
            for i, col_name in enumerate(col_names_from_row):
                try:
                    val = row[col_name]
                    result[col_name] = val
                except Exception:
                    try:
                        val = row[i]
                        result[col_name] = val
                    except Exception:
                        result[col_name] = None
            return result if result else row
    except Exception:
        pass
    
    return row
