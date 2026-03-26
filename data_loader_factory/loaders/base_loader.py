"""Base Loader - Abstract base class for all data loaders."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseLoader(ABC):
    """Abstract base class for loading test data from various formats."""
    
    @abstractmethod
    def load(self, file_path: str) -> Dict[str, Any]:
        """Load test data from file.
        
        Args:
            file_path: Path to the data file
            
        Returns:
            Dictionary containing test data, keyed by SP name
        """
        pass
