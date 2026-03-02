"""Test Case Builder - Builds test cases from data."""

from typing import Dict, Any, List, Optional
import datetime
import yaml
import os
from pathlib import Path


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


class ConfigLoader:
    """Loads and manages configuration from YAML files."""
    
    _config_cache: Dict[str, Any] = {}
    
    @staticmethod
    def load_config(config_path: str, config_type: str = 'database') -> Dict[str, Any]:
        """Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML config file
            config_type: Type of config ('database', 'test', 'all')
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If YAML is invalid
        """
        if config_path in ConfigLoader._config_cache:
            return ConfigLoader._config_cache[config_path]
        
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f) or {}
                ConfigLoader._config_cache[config_path] = config
                return config
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}")
    
    @staticmethod
    def get_database_config(config_path: str) -> Dict[str, Any]:
        """Load database configuration section.
        
        Args:
            config_path: Path to YAML config file
            
        Returns:
            Database config dictionary with keys: host, name, user, password
        """
        config = ConfigLoader.load_config(config_path)
        return config.get('database', {})
    
    @staticmethod
    def get_test_config(config_path: str) -> Dict[str, Any]:
        """Load test configuration section.
        
        Args:
            config_path: Path to YAML config file
            
        Returns:
            Test config dictionary with keys: timeout, retry_count, isolation_level, etc.
        """
        config = ConfigLoader.load_config(config_path)
        return config.get('test', {})
    
    @staticmethod
    def clear_cache():
        """Clear config cache."""
        ConfigLoader._config_cache.clear()


class TestCaseBuilder:
    """Builds and validates test cases from various sources."""
    
    def __init__(self, data_factory=None):
        """Initialize TestCaseBuilder.
        
        Args:
            data_factory: Optional DataLoaderFactory instance
        """
        if data_factory is None:
            from data_loader_factory import DataLoaderFactory
            data_factory = DataLoaderFactory()
        self.data_factory = data_factory
    
    def parse_and_validate_test_data(self, test_data: Dict) -> bool:
        """Validate test data structure.
        
        Args:
            test_data: Test data dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = ['input', 'expected_result']
        return all(key in test_data for key in required_keys)
    
    def create_test_objects(self, test_data_list: List[Dict]) -> List[Dict]:
        """Create test case objects from test data.
        
        Args:
            test_data_list: List of test data dictionaries
            
        Returns:
            List of validated test case objects
        """
        test_cases = []
        for test_data in test_data_list:
            if self.parse_and_validate_test_data(test_data):
                test_case = {
                    'id': test_data.get('id', f"test_{len(test_cases) + 1}"),
                    'name': test_data.get('name', ''),
                    'description': test_data.get('description', ''),
                    'input': test_data.get('input', {}),
                    'expected_result': test_data.get('expected_result', {}),
                    'stored_procedure': test_data.get('stored_procedure', ''),
                    'chain_procedures': test_data.get('chain_procedures', []),
                    'validations': test_data.get('validations', []),
                }
                test_cases.append(test_case)
        return test_cases
    
    def build_from_file(self, file_path: str) -> List[Dict]:
        """Build test cases from a file (JSON, CSV, Excel).
        
        Args:
            file_path: Path to test data file
            
        Returns:
            List of test case objects
        """
        loader = self.data_factory.get_loader(file_path)
        test_data_list = loader.load(file_path)
        return self.create_test_objects(test_data_list)
    
    def build_from_dict(self, test_dict: Dict) -> Dict:
        """Build a single test case from dictionary.
        
        Args:
            test_dict: Test case dictionary
            
        Returns:
            Validated test case object
        """
        if self.parse_and_validate_test_data(test_dict):
            return self.create_test_objects([test_dict])[0]
        raise ValueError("Invalid test data structure")
