"""Keyword-Driven CSV Loader - Load and transform keyword-driven test data from CSV to JSON format."""

import csv
import json
import os
import logging
from typing import Dict, Any, List
from .base_loader import BaseLoader

logger = logging.getLogger('sp_validation')


class KeywordDrivenCSVLoader(BaseLoader):
    """Load keyword-driven test data from CSV and transform to JSON structure."""
    
    @staticmethod
    def load(file_path: str) -> Dict[str, Any]:
        """Load test data from a keyword-driven CSV file.
        
        CSV Format:
        Module | Operation | Test Case ID | Executed | test_parameters (JSON string)
        
        Args:
            file_path: Path to the CSV file (with or without .csv extension)
            
        Returns:
            Dictionary containing test data keyed by module/SP name
            
        Example CSV Row:
        usp_CreateUpdateSchedulingTeam,Create,Create_New_Team_01,Yes,"{""name"":""TestTeam"",""divisionId"":6}"
        """
        # Ensure file path has .csv extension
        if not file_path.endswith('.csv'):
            file_path = f"{file_path}.csv"
        
        # Build path relative to data_layer/test_data/
        if not os.path.isabs(file_path):
            project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            file_path = os.path.join(project_root_dir, 'data_layer', 'test_data', file_path)
        
        logger.info(f"Loading keyword-driven CSV test data from: {file_path}")
        
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Test data file not found: {file_path}")
        
        try:
            data = {}
            
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    module = row.get('Module', '').strip()
                    operation = row.get('Operation', '').strip()
                    case_id = row.get('Test Case ID', '').strip()
                    executed = row.get('Executed', 'No').strip().lower() == 'yes'
                    test_type = row.get('Test Type', 'independent').strip()
                    params_json = row.get('test_parameters', '{}').strip()
                    
                    # Skip if module is empty
                    if not module:
                        logger.warning(f"Skipping row with empty Module: {row}")
                        continue
                    
                    # Initialize module entry if not exists
                    if module not in data:
                        data[module] = []
                    
                    # Parse test parameters JSON
                    try:
                        params = json.loads(params_json) if params_json else {}
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON in test_parameters for {case_id}: {e}")
                        params = {}
                    
                    # Build test case object
                    test_case = {
                        'case_id': case_id,
                        'case_type': operation.upper() if operation else 'POSITIVE',
                        'description': f"{operation} test case: {case_id}",
                        'operation': operation,
                        'executed': executed,
                        'test_type': test_type,
                        'parameters': params,
                        'expected_status': row.get('expected_status', '').strip(),
                        'expected_message_pattern': row.get('expected_message_pattern', '').strip()
                    }
                    
                    data[module].append(test_case)
            
            logger.info(f"Successfully loaded keyword-driven test data from {file_path}")
            logger.info(f"Loaded {len(data)} modules with total test cases")
            
            return data
            
        except csv.Error as e:
            logger.error(f"CSV parsing error in {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            raise
