"""JSON Loader - Load test data from JSON files."""

import json
import os
import logging
from typing import Dict, Any
from .base_loader import BaseLoader

logger = logging.getLogger('sp_validation')


class JSONLoader(BaseLoader):
    """Load test data from JSON files."""
    
    @staticmethod
    def load(file_path: str) -> Dict[str, Any]:
        """Load test data from a JSON file.
        
        Args:
            file_path: Path to the JSON file (with or without .json extension)
            
        Returns:
            Dictionary containing test data
        """
        # Ensure file path has .json extension
        if not file_path.endswith('.json'):
            file_path = f"{file_path}.json"
        
        # Check if file exists in data_layer/test_data/ directory
        if not os.path.isabs(file_path):
            # Build path relative to data_layer/test_data/
            project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            file_path = os.path.join(project_root_dir, 'data_layer', 'test_data', file_path)
        
        logger.info(f"Loading JSON test data from: {file_path}")
        
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Test data file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            logger.info(f"Successfully loaded test data from {file_path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading JSON file: {e}")
            raise
