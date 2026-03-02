"""Test Cases Component - Manages test case data structures."""

from typing import Dict, List, Any


class TestCase:
    """Represents a single test case with all its configuration."""
    
    def __init__(self, case_id: str, case_type: str, description: str, 
                 parameters: Dict[str, Any], chain_config: List[Dict] = None,
                 pre_sql: List = None, post_sql: List = None, 
                 cleanup_sql: List = None, expected_results: Dict = None,
                 expected_post_state: Dict = None):
        """Initialize a test case.
        
        Args:
            case_id: Unique identifier for the test case
            case_type: Type of test (POSITIVE, NEGATIVE, EDGE)
            description: Human-readable description
            parameters: Dictionary of input parameters
            chain_config: Optional list of chained SP configurations
            pre_sql: Optional SQL statements to run before SP execution
            post_sql: Optional SQL statements to run after SP execution
            cleanup_sql: Optional SQL statements for cleanup
            expected_results: Expected results configuration
            expected_post_state: Expected state after execution
        """
        self.case_id = case_id
        self.case_type = case_type
        self.description = description
        self.parameters = parameters
        self.chain_config = chain_config
        self.pre_sql = pre_sql or []
        self.post_sql = post_sql or []
        self.cleanup_sql = cleanup_sql or []
        self.expected_results = expected_results or {}
        self.expected_post_state = expected_post_state or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to dictionary."""
        return {
            'case_id': self.case_id,
            'case_type': self.case_type,
            'description': self.description,
            'parameters': self.parameters,
            'chain_config': self.chain_config,
            'pre_sql': self.pre_sql,
            'post_sql': self.post_sql,
            'cleanup_sql': self.cleanup_sql,
            'expected_results': self.expected_results,
            'expected_post_state': self.expected_post_state,
        }


class TestCaseBuilder:
    """Builder for constructing test cases from JSON data."""
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> TestCase:
        """Create a TestCase from a dictionary (typically from JSON).
        
        Args:
            data: Dictionary containing test case data
            
        Returns:
            TestCase instance
        """
        return TestCase(
            case_id=data.get('case_id', 'unknown'),
            case_type=data.get('case_type', 'POSITIVE'),
            description=data.get('description', ''),
            parameters=data.get('parameters', {}),
            chain_config=data.get('chain_config'),
            pre_sql=data.get('pre_sql'),
            post_sql=data.get('post_sql'),
            cleanup_sql=data.get('cleanup_sql'),
            expected_results=data.get('expected_results'),
            expected_post_state=data.get('expected_post_state'),
        )
    
    @staticmethod
    def from_list(data_list: List[Dict[str, Any]]) -> List[TestCase]:
        """Create multiple TestCases from a list of dictionaries.
        
        Args:
            data_list: List of dictionaries
            
        Returns:
            List of TestCase instances
        """
        return [TestCaseBuilder.from_dict(item) for item in data_list]
