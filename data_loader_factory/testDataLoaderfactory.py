"""Test Data Loader Factory - Automatically load test data from any format."""

import os
import logging
from typing import Dict, Any
from .fileLoader import (
    JSONLoader,
    CSVLoader,
    ExcelLoader,
)

logger = logging.getLogger('sp_validation')

# Cache loaded data to avoid redundant file I/O and logging
_data_cache = {}


class TestDataLoader:
    """
    Universal test data loader for various formats.
    
    Auto-detects format from file extension and uses the appropriate loader.
    Supports JSON, CSV (with automatic schema detection), and Excel (XLSX/XLS) formats.
    
    CSV files are automatically detected as either:
    - Keyword-driven format (Module/Operation/Test Case ID/etc.)
    - Generic format (sp_name)

    store class inside dict=like a variable
    """
    
    LOADERS = {
        '.json': JSONLoader,
        '.csv': CSVLoader,
        '.xlsx': ExcelLoader,
        '.xls': ExcelLoader,
    }
    
    @staticmethod
    def load(file_path: str, format: str = None, loader_type: str = None) -> Dict[str, Any]:
        """Load test data from a file with automatic format detection.
        
        Automatically detects format from file extension if not explicitly specified.
        For CSV files, automatically detects schema (keyword-driven or generic).
        Supports JSON, CSV, and Excel formats.
        
        Args:
            file_path: Path to the data file. Can include or exclude extension.
                      If no extension provided, defaults to JSON.
            format: Optional explicit format ('json', 'csv', 'xlsx', 'xls').
                   If not provided, auto-detects from file extension.
            loader_type: Deprecated. Previously used for 'keyword_driven' format.
                        CSV files now auto-detect schema automatically.
                        Parameter kept for backward compatibility.
        
        Returns:
            Dictionary containing test data keyed by module/SP name
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the format is not supported
            
        Examples:
            # Load JSON file (auto-detected)
            TestDataLoader.load('test_data.json')
            
            # Load CSV file (schema auto-detected: keyword-driven or generic)
            TestDataLoader.load('tests.csv')
            
            # Explicit format (no extension needed)
            TestDataLoader.load('test_data', format='json')
            
            # Load Excel file (auto-detected)
            TestDataLoader.load('test_data.xlsx')
        """
        # Note: loader_type parameter kept for backward compatibility but not used
        # CSV files automatically detect schema type (keyword-driven vs generic)
        
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
        loader_class = TestDataLoader.LOADERS.get(ext)
        if not loader_class:
            supported = ', '.join(TestDataLoader.LOADERS.keys())
            raise ValueError(f"Unsupported file format: {ext}. Supported formats: {supported}")
        
        # Normalize file path for cache key to handle relative/absolute path variations
        normalized_path = os.path.abspath(file_path) if os.path.exists(file_path) or os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)) else file_path.lower()
        cache_key = (normalized_path, ext)
        
        if cache_key in _data_cache:
            logger.debug(f"Using cached data for: {file_path}")
            return _data_cache[cache_key]
        
        logger.info(f"Using {loader_class.__name__} for: {file_path}")
        
        # Load and cache data
        data = loader_class.load(file_path)
        _data_cache[cache_key] = data
        return data


# Backward compatibility alias
DataLoaderFactory = TestDataLoader
