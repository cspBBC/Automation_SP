"""Row Count Validator - Validates row counts in results."""

import logging
from typing import List, Any

logger = logging.getLogger(__name__)


def validate_row_count(rows: List[Any], expected_count: int) -> bool:
    """Validate that result set has expected row count.
    
    Args:
        rows: List of result rows
        expected_count: Expected row count
        
    Returns:
        True if counts match, False otherwise
    """
    actual_count = len(rows) if rows else 0
    
    if actual_count == expected_count:
        logger.debug(f"Row count validation PASSED: {actual_count} == {expected_count}")
        return True
    else:
        logger.debug(f"Row count validation FAILED: {actual_count} != {expected_count}")
        return False


def validate_non_empty(rows: List[Any]) -> bool:
    """Validate that result set is not empty.
    
    Args:
        rows: List of result rows
        
    Returns:
        True if rows exist, False otherwise
    """
    has_rows = bool(rows and len(rows) > 0)
    logger.debug(f"Non-empty validation: {has_rows}")
    return has_rows


def validate_empty(rows: List[Any]) -> bool:
    """Validate that result set is empty.
    
    Args:
        rows: List of result rows
        
    Returns:
        True if no rows, False otherwise
    """
    is_empty = not rows or len(rows) == 0
    logger.debug(f"Empty validation: {is_empty}")
    return is_empty
