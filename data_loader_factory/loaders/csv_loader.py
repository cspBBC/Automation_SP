"""CSV Loader - Load test data from CSV files."""

import os
import csv
import logging
from typing import Dict, Any, List
from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class CSVLoader(BaseLoader):
    """Load test data from CSV files."""
    
    @staticmethod
    def load(file_path: str) -> Dict[str, Any]:
        """Load test data from a CSV file.
        
        Args:
            file_path: Path to the CSV file (with or without .csv extension)
            
        Returns:
            Dictionary containing test data keyed by SP name
        """
        # Ensure file path has .csv extension
        if not file_path.endswith('.csv'):
            file_path = f"{file_path}.csv"
        
        # Check if file exists in data_layer/test_data/ directory
        if not os.path.isabs(file_path):
            project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            file_path = os.path.join(project_root_dir, 'data_layer', 'test_data', file_path)
        
        logger.info(f"Loading CSV test data from: {file_path}")
        
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Test data file not found: {file_path}")
        
        try:
            data = {}
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sp_name = row.get('sp_name', 'unknown')
                    if sp_name not in data:
                        data[sp_name] = []
                    data[sp_name].append(row)
            
            logger.info(f"Successfully loaded test data from {file_path}")
            return data
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            raise
