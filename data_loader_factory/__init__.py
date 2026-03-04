"""Test Data Loader - Load test data from various formats (JSON, CSV, Excel)."""

from .factory import TestDataLoader, DataLoaderFactory
from .loader import (
    BaseLoader,
    JSONLoader,
    CSVLoader,
    ExcelLoader,
)

__all__ = [
    'TestDataLoader',
    'DataLoaderFactory',  # Backward compatibility
    'BaseLoader',
    'JSONLoader',
    'CSVLoader',
    'ExcelLoader',
]
