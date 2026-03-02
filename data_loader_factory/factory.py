"""Data Loader Factory - Automatically select appropriate loader based on file format."""

import os
import logging
from typing import Dict, Any
from .loaders.base_loader import BaseLoader
from .loaders.json_loader import JSONLoader
from .loaders.csv_loader import CSVLoader
from .loaders.excel_loader import ExcelLoader
from .loaders.keyword_driven_loader import KeywordDrivenCSVLoader

logger = logging.getLogger(__name__)


class DataLoaderFactory:
    """Factory for loading test data from various sources (CSV, Excel, JSON)."""
    
    _LOADERS = {
        '.json': JSONLoader,
        '.csv': CSVLoader,
        '.xlsx': ExcelLoader,
        '.xls': ExcelLoader,
    }
    
    @staticmethod
    def load(file_path: str, format: str = None, loader_type: str = None) -> Dict[str, Any]:
        """Load test data from a file.
        
        Automatically detects format from file extension if not explicitly specified.
        Supports JSON, CSV, Excel, and keyword-driven CSV formats.
        
        Args:
            file_path: Path to the data file. Can include or exclude extension.
                      If no extension provided, defaults to JSON.
            format: Optional explicit format ('json', 'csv', 'xlsx', 'xls').
                   If not provided, auto-detects from file extension.
            loader_type: Optional explicit loader type:
                        - 'keyword_driven' for keyword-driven CSV format
                        - Otherwise uses default loader for format
        
        Returns:
            Dictionary containing test data keyed by SP name
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the format is not supported
            
        Examples:
            # Load JSON file
            DataLoaderFactory.load('test_data.json')
            
            # Load keyword-driven CSV
            DataLoaderFactory.load('keyword_tests.csv', loader_type='keyword_driven')
            
            # Explicit format
            DataLoaderFactory.load('test_data', format='json')
        """
        # Handle keyword-driven loader explicitly
        if loader_type and loader_type.lower() == 'keyword_driven':
            logger.info(f"Using KeywordDrivenCSVLoader to load: {file_path}")
            return KeywordDrivenCSVLoader.load(file_path)
        
        # Determine file extension
        if format:
            # Explicit format provided
            ext = f".{format.lower()}" if not format.startswith('.') else format.lower()
        else:
            # Auto-detect from file path
            _, ext = os.path.splitext(file_path.lower())
            if not ext:
                # No extension - default to JSON
                ext = '.json'
        
        # Get appropriate loader
        loader_class = DataLoaderFactory._LOADERS.get(ext)
        if not loader_class:
            raise ValueError(f"Unsupported file format: {ext}. Supported formats: {list(DataLoaderFactory._LOADERS.keys())}")
        
        logger.info(f"Using {loader_class.__name__} to load: {file_path}")
        
        # Load and return data
        return loader_class.load(file_path)
