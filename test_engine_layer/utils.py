"""Utils - Simple logging, formatting, and test data utilities."""

import sys
import logging
from pathlib import Path
from typing import List, Dict
from config.config import DataConfig


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    @staticmethod
    def fail(text):
        """Format text as failure (red)."""
        return f"{Colors.RED}{Colors.BOLD}{text}{Colors.RESET}"
    
    @staticmethod
    def success(text):
        """Format text as success (green)."""
        return f"{Colors.GREEN}{Colors.BOLD}{text}{Colors.RESET}"
    
    @staticmethod
    def info(text):
        """Format text as info (blue)."""
        return f"{Colors.BLUE}{text}{Colors.RESET}"
    
    @staticmethod
    def warn(text):
        """Format text as warning (yellow)."""
        return f"{Colors.YELLOW}{text}{Colors.RESET}"


def setup_logging():
    """Setup console logging."""
    logger = logging.getLogger('sp_validation')
    logger.setLevel(logging.DEBUG)
    
    # Remove existing console handlers to avoid duplicates
    for handler in logger.handlers[:]:
        if not isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)
    
    # Console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


def load_test_data(data_file: str = None) -> Dict:
    """Load test data from CSV/Excel/JSON file.
    
    Args:
        data_file: Optional data file path. Defaults to configured file.
        
    Returns:
        Dict of {module_name: [test_case_rows]}
    """
    from data_loader_factory import TestDataLoader
    
    if data_file is None:
        data_file = DataConfig.DEFAULT_TEST_DATA_FILE
    
    return TestDataLoader.load(data_file)


def get_test_case_ids_by_operation(operation: str, data_file: str = None) -> List[str]:
    """Get enabled test case IDs for an operation.
    
    Args:
        operation: Operation type (e.g., 'Create', 'Edit')
        data_file: Optional data file path
        
    Returns:
        List of enabled test case IDs
    """
    test_data = load_test_data(data_file)
    test_cases = []
    
    for module_name, cases in test_data.items():
        for row in cases:
            test_name = row.get('case_id', '').strip()
            op = row.get('operation', '').strip()
            executed_raw = row.get('executed', False)
            
            # Convert string 'True'/'False' to boolean
            if isinstance(executed_raw, str):
                executed = executed_raw.lower() == 'true'
            else:
                executed = bool(executed_raw)
            
            if op.lower() == operation.lower() and executed:
                test_cases.append(test_name)
    
    return test_cases


def get_module_for_test_case(test_case_id: str, data_file: str = None) -> str:
    """Get the module name for a test case.
    
    Args:
        test_case_id: Test case ID
        data_file: Optional data file path
        
    Returns:
        Module name
        
    Raises:
        ValueError: If test case not found
    """
    test_data = load_test_data(data_file)
    
    for module_name, cases in test_data.items():
        for row in cases:
            if row.get('case_id', '').strip() == test_case_id:
                return module_name
    
    raise ValueError(f"Test case '{test_case_id}' not found in test data")


def validate_test_configuration(data_file: str = None) -> None:
    """Validate test configuration - works with CSV/XLSX/JSON. Ensure if any non-Create test is enabled, at least one Create is enabled.
    
    Args:
        data_file: Optional data file path
        
    Raises:
        AssertionError: If configuration is invalid
    """
    test_data = load_test_data(data_file)
    
    logger = setup_logging()
    
    # Get all enabled tests grouped by operation
    enabled_by_operation = {}
    for module_name, cases in test_data.items():
        for row in cases:
            op = row.get('operation', '').strip()
            executed_raw = row.get('executed', False)
            case_id = row.get('case_id', '').strip()
            
            # Convert string 'True'/'False' to boolean
            if isinstance(executed_raw, str):
                executed = executed_raw.lower() == 'true'
            else:
                executed = bool(executed_raw)
            
            if executed:
                if op not in enabled_by_operation:
                    enabled_by_operation[op] = []
                enabled_by_operation[op].append(case_id)
    
    # Get all enabled Create tests
    enabled_creates = enabled_by_operation.get('Create', []) or enabled_by_operation.get('create', [])
    
    # Filter out Duplicate Creates (they need a regular Create to duplicate from)
    regular_creates = [tc for tc in enabled_creates if 'Duplicate' not in tc]
    
    # Check 1: Normal operations (Edit, etc.) require at least one Create
    for operation, test_ids in enabled_by_operation.items():
        if operation.lower() not in ['create']:
            if not enabled_creates:
                error_msg = (
                    f"Configuration Error: {operation} test(s) enabled but no Create test is enabled.\n"
                    f"  {operation} tests enabled: {', '.join(test_ids)}\n"
                    f"Please enable at least one Create test (Executed=yes) in test data"
                )
                logger.error(error_msg)
                raise AssertionError(error_msg)
    
    # Check 2: Duplicate test requires at least one REGULAR (non-Duplicate) Create
    duplicate_creates = [tc for tc in enabled_creates if 'Duplicate' in tc]
    if duplicate_creates and not regular_creates:
        error_msg = (
            f"Configuration Error: Duplicate test(s) enabled but no regular Create test is enabled.\n"
            f"  Duplicate tests enabled: {', '.join(duplicate_creates)}\n"
            f"  For duplicate prevention testing: both baseline Create AND Duplicate test must be in same transaction.\n"
            f"Please enable at least one regular Create test (e.g., Create_New_Schd_Team_01=yes) in test data\n"
            f"  NOTE: Duplicate test MUST use SAME schedulingTeamName and divisionId as the baseline Create test!"
        )
        logger.error(error_msg)
        raise AssertionError(error_msg)
    
    # Check 3: If Duplicate enabled, verify it has SAME schedulingTeamName and divisionId as baseline Create
    if duplicate_creates and regular_creates:
        # Build a map of test cases to their parameters
        test_params = {}
        for module_name, cases in test_data.items():
            for row in cases:
                case_id = row.get('case_id', '').strip()
                # Try 'parameters' (from CSV loader) first, then 'test_parameters' (raw CSV)
                params = row.get('parameters', row.get('test_parameters', {}))
                if isinstance(params, str):
                    try:
                        import json
                        params = json.loads(params)
                    except:
                        pass
                test_params[case_id] = params
        
        # Get baseline Create parameters
        baseline_create = regular_creates[0]  # First enabled regular Create
        baseline_params = test_params.get(baseline_create, {})
        baseline_schd_name = baseline_params.get('schedulingTeamName', '')
        baseline_div_id = baseline_params.get('divisionId', '')
        
        # Check each Duplicate test
        for dup_test in duplicate_creates:
            dup_params = test_params.get(dup_test, {})
            dup_schd_name = dup_params.get('schedulingTeamName', '')
            dup_div_id = dup_params.get('divisionId', '')
            
            if (dup_schd_name != baseline_schd_name) or (dup_div_id != baseline_div_id):
                error_msg = (
                    f"Configuration Error: Duplicate test parameters don't match baseline Create.\n"
                    f"  For duplicate prevention, Duplicate test MUST use:\n"
                    f"    - SAME schedulingTeamName as baseline Create\n"
                    f"    - SAME divisionId as baseline Create\n"
                    f"  Baseline Create ({baseline_create}):\n"
                    f"    - schedulingTeamName: {baseline_schd_name}\n"
                    f"    - divisionId: {baseline_div_id}\n"
                    f"  Duplicate test ({dup_test}):\n"
                    f"    - schedulingTeamName: {dup_schd_name}\n"
                    f"    - divisionId: {dup_div_id}\n"
                    f"  Please update {dup_test} to use same scheduling team name and division ID as {baseline_create} in test data"
                )
                logger.error(error_msg)
                raise AssertionError(error_msg)



def get_test_parameters(test_case_id: str, data_file: str = None) -> Dict:
    """Get the parameters for a test case.
    
    Args:
        test_case_id: Test case ID
        data_file: Optional data file path
        
    Returns:
        Dict of test parameters
    """
    test_data = load_test_data(data_file)
    
    for module_name, cases in test_data.items():
        for row in cases:
            if row.get('case_id', '').strip() == test_case_id:
                return row.get('test_parameters', {})
    
    return {}
