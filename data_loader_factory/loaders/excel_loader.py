"""Excel Loader - Load test data from Excel files."""

import os
import logging
from typing import Dict, Any
from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class ExcelLoader(BaseLoader):
    """Load test data from Excel files.
    
    Requires openpyxl or xlrd package to be installed.
    """
    
    @staticmethod
    def load(file_path: str) -> Dict[str, Any]:
        """Load test data from an Excel file.
        
        Args:
            file_path: Path to the Excel file (with or without .xlsx/.xls extension)
            
        Returns:
            Dictionary containing test data keyed by SP name
        """
        try:
            import openpyxl
        except ImportError:
            raise ImportError("openpyxl is required to load Excel files. Install it with: pip install openpyxl")
        
        # Ensure file path has .xlsx extension if not specified
        if not file_path.endswith(('.xlsx', '.xls')):
            file_path = f"{file_path}.xlsx"
        
        # Check if file exists in data_layer/test_data/ directory
        if not os.path.isabs(file_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(base_dir, 'test_data', file_path)
        
        logger.info(f"Loading Excel test data from: {file_path}")
        
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Test data file not found: {file_path}")
        
        try:
            data = {}
            wb = openpyxl.load_workbook(file_path)
            
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                headers = [cell.value for cell in ws[1]]
                
                for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
                    row_dict = dict(zip(headers, row))
                    sp_name = row_dict.get('sp_name', 'unknown')
                    
                    if sp_name not in data:
                        data[sp_name] = []
                    data[sp_name].append(row_dict)
            
            logger.info(f"Successfully loaded test data from {file_path}")
            return data
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            raise
