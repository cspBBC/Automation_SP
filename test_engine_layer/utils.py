"""Utils - Logging, formatting, and test data utilities."""

import sys
import logging
from pathlib import Path
from typing import List
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
    """Setup console logging while preserving any file handlers.
    
    Removes console handlers to avoid duplicates but preserves file handlers
    that may have been added by test fixtures.
    
    Returns the logger.
    """
    logger = logging.getLogger('sp_validation')
    logger.setLevel(logging.DEBUG)
    
    # Remove existing console handlers to avoid duplicates, but preserve file handlers
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


def get_test_case_ids_by_operation(operation: str, test_type: str = None, data_file: str = None) -> List[str]:
    """Load test case IDs from test data filtered by operation type and execution status.
    
    Filters the keyword-driven test data (CSV/Excel/JSON) to return only test case IDs where:
    - The Operation field matches the specified operation (case-insensitive)
    - The Executed field is 'Yes' (case-insensitive)
    - The Test Type field matches the specified type (optional, case-insensitive)
    
    Format is auto-detected from file extension (CSV/XLSX/XLS/JSON).
    
    Args:
        operation: Operation type to filter by (e.g., 'Create', 'Edit', 'Delete')
        test_type: Optional test type to filter by (e.g., 'independent', 'scenario', 'workflow')
        data_file: Optional data file name (defaults to configured DEFAULT_TEST_DATA_FILE). Format auto-detected from extension.
        
    Returns:
        List of test case IDs matching the criteria, in data file order
        
    Example:
        >>> create_tests = get_test_case_ids_by_operation('Create')
        >>> independent_tests = get_test_case_ids_by_operation('Create', test_type='independent')
        >>> scenario_tests = get_test_case_ids_by_operation('Create', test_type='scenario')
        >>> from_excel = get_test_case_ids_by_operation('Create', data_file='custom_tests.xlsx')
    """
    from data_loader_factory import TestDataLoader
    
    # Default to configured data file if not specified
    if data_file is None:
        data_file = DataConfig.DEFAULT_TEST_DATA_FILE
    
    # Load test data using format-agnostic loader (auto-detects format and schema)
    test_data = TestDataLoader.load(data_file)
    test_cases = []
    
    # Iterate through all modules and their test cases
    for module_name, cases in test_data.items():
        for row in cases:
            test_name = row.get('case_id', '').strip()
            op = row.get('operation', '').strip()
            executed = row.get('executed', False)
            tt = row.get('test_type', '').strip()
            
            # Include tests matching operation and executed status
            if op.lower() == operation.lower() and executed:
                # If test_type specified, also check it
                if test_type is None or tt.lower() == test_type.lower():
                    test_cases.append(test_name)
    
    return test_cases


# Module to preseed file mappings
# Add new modules here as they are introduced to the framework
MODULE_PRESEED_FILES = {
    'usp_CreateUpdateSchedulingTeam': [
        'createSchdGroup_user.sql',
        'createSchdGroup_division.sql'
    ],
    # Add more modules as needed:
    # 'usp_ModuleTwo': ['preseed_module_two_users.sql', 'preseed_module_two_configs.sql'],
    # 'usp_ModuleThree': ['preseed_module_three_data.sql'],
}


def get_module_for_test_case(test_case_id: str, data_file: str = None) -> str:
    """Get the module name for a given test case ID.
    
    Looks up the test case in test data (CSV/Excel/JSON) and returns its module name.
    Format is auto-detected from file extension.
    
    Args:
        test_case_id: Test case ID to look up
        data_file: Optional data file name (defaults to configured DEFAULT_TEST_DATA_FILE). Format auto-detected from extension.
        
    Returns:
        Module name for the test case
        
    Raises:
        ValueError: If test case not found in test data
        
    Example:
        >>> module = get_module_for_test_case('Create_New_Schd_Team_01')
        >>> # Returns: 'usp_CreateUpdateSchedulingTeam'
    """
    from data_loader_factory import TestDataLoader
    
    # Default to configured data file if not specified
    if data_file is None:
        data_file = DataConfig.DEFAULT_TEST_DATA_FILE
    
    # Load test data using format-agnostic loader (auto-detects format and schema)
    test_data = TestDataLoader.load(data_file)
    
    # Search through all modules for the test case
    for module_name, cases in test_data.items():
        for row in cases:
            if row.get('case_id', '').strip() == test_case_id:
                return module_name
    
    raise ValueError(f"Test case '{test_case_id}' not found in test data file '{data_file}'")


def get_test_type_for_test_case(test_case_id: str, data_file: str = None) -> str:
    """Get the test type for a given test case ID.
    
    Looks up the test case in test data (CSV/Excel/JSON) and returns its Test Type.
    Format is auto-detected from file extension.
    
    Test types determine execution mode:
    - 'independent': Test case runs in isolated transaction with filter_test_name
    - 'scenario': Test case runs in shared transaction with other scenario tests
    - 'workflow': Test case part of multi-step workflow (Create→Edit, etc.)
    
    Args:
        test_case_id: Test case ID to look up
        data_file: Optional data file name (defaults to configured DEFAULT_TEST_DATA_FILE). Format auto-detected from extension.
        
    Returns:
        Test type for the test case (default: 'independent')
        
    Example:
        >>> test_type = get_test_type_for_test_case('Create_Duplicate_Team_01')
        >>> # Returns: 'scenario'
    """
    from data_loader_factory import TestDataLoader
    
    # Default to configured data file if not specified
    if data_file is None:
        data_file = DataConfig.DEFAULT_TEST_DATA_FILE
    
    # Load test data using format-agnostic loader (auto-detects format and schema)
    test_data = TestDataLoader.load(data_file)
    
    # Search through all modules for the test case
    for module_name, cases in test_data.items():
        for row in cases:
            if row.get('case_id', '').strip() == test_case_id:
                test_type = row.get('test_type', 'independent').strip()
                return test_type if test_type else 'independent'
    
    # Default to 'independent' if test case not found
    return 'independent'


def verify_preseed_for_module(module_name: str, request=None) -> bool:
    """Verify that all required preseed files exist for a given module.
    
    Checks if the preseed SQL files required by a module are present in the
    preseed_data directory. This ensures test data prerequisites are available
    before tests execute.
    
    Args:
        module_name: Name of the module (e.g., 'usp_CreateUpdateSchedulingTeam')
        request: Optional pytest request object (for better error reporting)
        
    Returns:
        True if all preseed files exist, False otherwise
        
    Raises:
        AssertionError: If required preseed files are missing
        
    Example:
        >>> verify_preseed_for_module('usp_CreateUpdateSchedulingTeam')  # Returns True
        >>> # Or use in a fixture:
        >>> verify_preseed_for_module('usp_CreateUpdateSchedulingTeam', request)
    """
    preseed_dir = Path(__file__).parent.parent / 'data_layer' / 'preseed_data'
    
    # If module not in mapping, no preseed required
    if module_name not in MODULE_PRESEED_FILES:
        logger = setup_logging()
        logger.debug(f"Module '{module_name}' has no preseed requirements")
        return True
    
    required_files = MODULE_PRESEED_FILES[module_name]
    missing_files = []
    
    for preseed_file in required_files:
        file_path = preseed_dir / preseed_file
        if not file_path.exists():
            missing_files.append(str(file_path))
    
    # Raise error if files are missing
    if missing_files:
        error_msg = f"Missing preseed files for module '{module_name}':\n"
        for f in missing_files:
            error_msg += f"  - {f}\n"
        raise AssertionError(error_msg.strip())
    
    return True
