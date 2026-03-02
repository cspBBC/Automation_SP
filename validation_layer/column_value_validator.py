"""Column Value Validator - Validates individual column values."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def validate_column_value(row: Dict[str, Any], column_name: str, expected_value: Any) -> bool:
    """Validate that a column has an expected value.
    
    Args:
        row: Row dictionary
        column_name: Column name to validate
        expected_value: Expected value
        
    Returns:
        True if actual matches expected, False otherwise
    """
    # Try exact match first
    if column_name in row:
        actual_value = row[column_name]
    else:
        # Try case-insensitive match
        for key in row.keys():
            if key.lower() == column_name.lower():
                actual_value = row[key]
                break
        else:
            logger.warning(f"Column '{column_name}' not found in row")
            return False
    
    if actual_value == expected_value:
        logger.debug(f"Column validation PASSED: {column_name}={actual_value}")
        return True
    else:
        logger.debug(f"Column validation FAILED: {column_name}={actual_value} (expected {expected_value})")
        return False


def validate_all_columns(row: Dict[str, Any], expected_columns: Dict[str, Any]) -> bool:
    """Validate that all columns in row match expected values.
    
    Args:
        row: Row dictionary
        expected_columns: Dictionary of column_name -> expected_value
        
    Returns:
        True if all columns match, False otherwise
    """
    all_match = True
    
    for col_name, expected_val in expected_columns.items():
        if not validate_column_value(row, col_name, expected_val):
            all_match = False
    
    return all_match
