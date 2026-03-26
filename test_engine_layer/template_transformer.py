"""Template Transformer - Transforms keyword-driven test data into generic template.

Supports multiple formats (CSV, Excel, JSON, etc) - format auto-detected from file extension.
"""

import json
import logging
import os
from typing import Dict, List, Any
from data_loader_factory import TestDataLoader
from config.config import DataConfig

logger = logging.getLogger('sp_validation')


class TemplateTransformer:
    """Transform keyword-driven test data into populated JSON templates.
    
    Supports any format (CSV, Excel, JSON, etc) - format auto-detected from file extension.
    """
    
    @staticmethod
    def load_and_transform(data_file: str, template_file: str = None, filter_executed: bool = True, module_filter: str = None, filter_test_name: str = None) -> Dict[str, Any]:
        """Load test data and transform using generic template.
        
        Args:
            data_file: Path to keyword-driven test data file (CSV/XLSX/XLS/JSON)
            template_file: Path to generic template JSON (default: generic_template.json).
                Can point at an operation-specific template file; regardless of the
                filename the JSON must use the module/sp name as its top-level key
                so that the loader can locate the right section.
            filter_executed: If True, only load rows where Executed='Yes'
            module_filter: Optional - only return data for specific module/SP name
            filter_test_name: Optional - only return data for specific test name (for independent test execution)
            
        Returns:
            Transformed test data dictionary ready for execution
            
        Example:
            data = TemplateTransformer.load_and_transform(
                'custom_data.xlsx',
                template_file='data_layer/test_data/module_template.json',
                filter_executed=True,
                module_filter='usp_Module',
                filter_test_name='Test_Case_01'
            )
        """
        if template_file is None:
            template_file = 'data_layer/test_data/generic_template.json'
        
        
        logger.info(f"Data File Path: {os.path.abspath(data_file) if os.path.exists(data_file) else data_file}")
        logger.info(f"Template Reference File: {os.path.abspath(template_file) if os.path.exists(template_file) else template_file}")
        if os.path.exists(template_file):
            logger.info(f"  File size: {os.path.getsize(template_file)} bytes")
        if module_filter:
            logger.info(f"Filtering to module: {module_filter}")
        
        # Load test data from file (format and schema auto-detected)
        test_data = TestDataLoader.load(data_file)
        
        # Load template
        with open(template_file, 'r', encoding='utf-8') as f:
            template = json.load(f)
        
        logger.info(f"Loaded template with {len(template)} modules\n")
        
        # Transform and populate
        transformed_data = {}
        
        for module_name, test_cases in test_data.items():
            # Filter by module if specified
            if module_filter and module_name != module_filter:
                continue
            
            logger.info(f"Processing module: {module_name}")
            transformed_cases = []
            
            for test_case in test_cases:
                # Filter by Executed status
                if filter_executed and not test_case.get('executed', False):
                    logger.debug(f"Skipping test case {test_case.get('case_id')} (not executed)")
                    continue
                
                # Filter by test name if specified (for independent test execution)
                if filter_test_name and test_case.get('case_id') != filter_test_name:
                    logger.debug(f"Skipping test case {test_case.get('case_id')} (not matching filter: {filter_test_name})")
                    continue
                
                # Populate template with test data values
                populated_case = TemplateTransformer._populate_template(
                    template.get(module_name, [{}])[0] if module_name in template else {},
                    test_case
                )
                
                # Module should remain the stored-procedure/module name, not the data "Operation" value
                populated_case['Module'] = module_name
                populated_case['Operation'] = test_case.get('operation', '')
                populated_case['Test Case ID'] = test_case.get('case_id', '')
                
                # Preserve CSV columns for validation (from expected_result CSV column)
                if test_case.get('expected_status'):
                    populated_case['expected_status'] = test_case.get('expected_status')
                if test_case.get('expected_result'):
                    populated_case['expected_result'] = test_case.get('expected_result')
                if test_case.get('expected_message_pattern'):
                    populated_case['expected_message_pattern'] = test_case.get('expected_message_pattern')
                if test_case.get('test_description'):
                    populated_case['test_description'] = test_case.get('test_description')
                
                transformed_cases.append(populated_case)
                logger.debug(f"Populated test case: {test_case.get('case_id')}")
            
            if transformed_cases:
                transformed_data[module_name] = transformed_cases
                logger.info(f"Module {module_name}: {len(transformed_cases)} test cases")
        
        logger.info(f"Transformation complete: {sum(len(v) for v in transformed_data.values())} total test cases")
        return transformed_data
    
    @staticmethod
    def _populate_template(template: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Populate template with test data values.
        
        Args:
            template: Template dictionary with placeholders
            data: Test data row with actual values
            
        Returns:
            Populated template with values from test data
        """
        import copy
        
        # Deep copy to avoid modifying original
        result = copy.deepcopy(template)
        
        # Get parameters from test data
        params = data.get('parameters', {})
        
        # Replace placeholders in chain_config
        if 'chain_config' in result:
            for step in result['chain_config']:
                if 'parameters' in step:
                    step['parameters'] = TemplateTransformer._replace_placeholders(
                        step['parameters'],
                        params
                    )
        
        return result
    
    @staticmethod
    def _replace_placeholders(obj: Any, params: Dict[str, Any]) -> Any:
        """Recursively replace placeholders with actual values.
        
        Args:
            obj: Object (dict, list, or value) with placeholders
            params: Dictionary of parameter values
            
        Returns:
            Object with placeholders replaced
        """
        if isinstance(obj, dict):
            return {k: TemplateTransformer._replace_placeholders(v, params) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [TemplateTransformer._replace_placeholders(item, params) for item in obj]
        elif isinstance(obj, str):
            # Replace placeholder if it exists in params
            if obj.startswith('{') and obj.endswith('}'):
                key = obj[1:-1]  # Remove { }
                # Handle different parameter name formats
                if key in params:
                    return params[key]
                elif f"@{key}" in params:
                    return params[f"@{key}"]
            return obj
        else:
            return obj


if __name__ == "__main__":
    # Example usage
    data = TemplateTransformer.load_and_transform(
        'test_data.csv',
        filter_executed=True
    )
    logger.info(json.dumps(data, indent=2))
