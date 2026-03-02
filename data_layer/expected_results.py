"""Expected Results Component - Manages expected result validation data."""

from typing import Dict, List, Any


class ExpectedResults:
    """Represents expected results for a test case."""
    
    def __init__(self, expected_config: Dict[str, Any] = None):
        """Initialize with expected results configuration.
        
        Args:
            expected_config: Configuration for expected results (row count, column values, etc.)
        """
        self.config = expected_config or {}
    
    def get_row_count_expectation(self) -> int:
        """Get expected row count if specified.
        
        Returns:
            Expected row count or None
        """
        return self.config.get('row_count')
    
    def get_column_expectations(self) -> Dict[str, Any]:
        """Get expected column values.
        
        Returns:
            Dictionary of column_name -> expected_value
        """
        return self.config.get('expected_columns', {})
    
    def get_return_code_expectation(self) -> int:
        """Get expected return code if specified.
        
        Returns:
            Expected return code or None
        """
        return self.config.get('return_code')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Configuration dictionary
        """
        return self.config.copy()


class PostStateValidator:
    """Manages post-execution state validation configuration."""
    
    def __init__(self, expected_post_state: List[Dict[str, Any]] = None):
        """Initialize with expected post-state configuration.
        
        Args:
            expected_post_state: List of post-state expectations (row counts, column values, etc.)
        """
        if expected_post_state is None:
            self.expectations = []
        elif isinstance(expected_post_state, dict):
            self.expectations = [expected_post_state]
        else:
            self.expectations = expected_post_state
    
    def add_expectation(self, expectation: Dict[str, Any]) -> None:
        """Add a post-state expectation.
        
        Args:
            expectation: Dictionary with expectation configuration
        """
        self.expectations.append(expectation)
    
    def get_all_expectations(self) -> List[Dict[str, Any]]:
        """Get all post-state expectations.
        
        Returns:
            List of expectation dictionaries
        """
        return self.expectations.copy()
    
    def has_expectations(self) -> bool:
        """Check if any expectations are defined.
        
        Returns:
            True if expectations exist
        """
        return len(self.expectations) > 0
