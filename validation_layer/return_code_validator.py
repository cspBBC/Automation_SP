"""Return Code Validator - Validates stored procedure return codes."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def validate_return_code(return_code: Any, expected_code: int) -> bool:
    """Validate that returned code matches expected value.
    
    Args:
        return_code: Actual return code from SP
        expected_code: Expected return code
        
    Returns:
        True if codes match, False otherwise
    """
    actual = int(return_code) if return_code is not None else None
    expected = int(expected_code)
    
    if actual == expected:
        logger.debug(f"Return code validation PASSED: {actual} == {expected}")
        return True
    else:
        logger.debug(f"Return code validation FAILED: {actual} != {expected}")
        return False


def extract_return_code(result: Dict) -> int:
    """Extract return code from result dictionary.
    
    Args:
        result: Result dictionary with 'output_params' key
        
    Returns:
        Return code value or 0 if not found
    """
    if isinstance(result, dict) and 'output_params' in result:
        output_params = result['output_params']
        # Common return code parameter names
        for param_name in ['@return_value', 'ReturnValue', 'return_value']:
            if param_name in output_params:
                return output_params[param_name]
    return 0
