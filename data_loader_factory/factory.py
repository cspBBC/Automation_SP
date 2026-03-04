"""Test Data Loader Factory - Automatically load test data from any format."""

import os
import logging
from typing import Dict, Any
from .loader import (
    BaseLoader,
    JSONLoader,
    CSVLoader,
    ExcelLoader,
    KeywordDrivenLoader
)

logger = logging.getLogger(__name__)


class TestDataLoader:
    """
    Universal test data loader for various formats.
    
    Auto-detects format from file extension and uses the appropriate loader.
    Supports JSON, CSV, Excel (XLSX/XLS), and keyword-driven CSV formats.
    """
    
    _LOADERS = {
        '.json': JSONLoader,
        '.csv': CSVLoader,
        '.xlsx': ExcelLoader,
        '.xls': ExcelLoader,
    }
    
    @staticmethod
    def load(file_path: str, format: str = None, loader_type: str = None) -> Dict[str, Any]:
        """Load test data from a file with automatic format detection.
        
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
            Dictionary containing test data keyed by module/SP name
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the format is not supported
            
        Examples:
            # Load JSON file (auto-detected)
            TestDataLoader.load('test_data.json')
            
            # Load keyword-driven CSV
            TestDataLoader.load('keyword_tests.csv', loader_type='keyword_driven')
            
            # Explicit format (no extension needed)
            TestDataLoader.load('test_data', format='json')
            
            # Load Excel file (auto-detected)
            TestDataLoader.load('test_data.xlsx')
        """
        # Handle keyword-driven loader explicitly
        if loader_type and loader_type.lower() == 'keyword_driven':
            logger.info(f"Using KeywordDrivenLoader for: {file_path}")
            return KeywordDrivenLoader.load(file_path)
        
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
        loader_class = TestDataLoader._LOADERS.get(ext)
        if not loader_class:
            supported = ', '.join(TestDataLoader._LOADERS.keys())
            raise ValueError(f"Unsupported file format: {ext}. Supported formats: {supported}")
        
        logger.info(f"Using {loader_class.__name__} for: {file_path}")
        
        # Load and return data
        return loader_class.load(file_path)


# Backward compatibility alias
DataLoaderFactory = TestDataLoader
