"""Input Parameters Component - Manages input parameter data."""

from typing import Dict, Any, List


class InputParameters:
    """Represents input parameters for a test case."""
    
    def __init__(self, parameters: Dict[str, Any]):
        """Initialize with parameter dictionary.
        
        Args:
            parameters: Dictionary mapping parameter names (with or without @) to values
        """
        self.parameters = self._normalize_params(parameters)
    
    def _normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parameter names (remove @ prefix if present).
        
        Args:
            params: Raw parameters dictionary
            
        Returns:
            Normalized parameters dictionary
        """
        normalized = {}
        for key, value in params.items():
            clean_key = key.lstrip('@')
            normalized[clean_key] = value
        return normalized
    
    def get_all(self) -> Dict[str, Any]:
        """Get all parameters."""
        return self.parameters.copy()
    
    def get(self, name: str, default: Any = None) -> Any:
        """Get a specific parameter value.
        
        Args:
            name: Parameter name (with or without @ prefix)
            default: Default value if not found
            
        Returns:
            Parameter value or default
        """
        clean_name = name.lstrip('@')
        return self.parameters.get(clean_name, default)
    
    def set(self, name: str, value: Any) -> None:
        """Set a parameter value.
        
        Args:
            name: Parameter name
            value: New value
        """
        clean_name = name.lstrip('@')
        self.parameters[clean_name] = value
    
    def merge(self, other_params: Dict[str, Any]) -> 'InputParameters':
        """Merge with another set of parameters.
        
        Args:
            other_params: Parameters to merge
            
        Returns:
            New InputParameters instance with merged values
        """
        merged = self.parameters.copy()
        other_normalized = self._normalize_params(other_params)
        merged.update(other_normalized)
        return InputParameters(merged)
    
    def override(self, overrides: Dict[str, Any]) -> 'InputParameters':
        """Create a new instance with overridden parameters.
        
        Args:
            overrides: Parameters to override
            
        Returns:
            New InputParameters instance with overrides applied
        """
        return self.merge(overrides)
