"""Template Transformer - Transforms keyword-driven CSV data into generic template."""

import json
import logging
import os
from typing import Dict, List, Any
from data_loader_factory import DataLoaderFactory

logger = logging.getLogger(__name__)


class TemplateTransformer:
    """Transform keyword-driven CSV data into populated JSON templates."""
    
    @staticmethod
    def load_and_transform(csv_file: str, template_file: str = None, filter_executed: bool = True, module_filter: str = None) -> Dict[str, Any]:
        """Load CSV data and transform using generic template.
        
        Args:
            csv_file: Path to keyword-driven CSV file
            template_file: Path to generic template JSON (default: generic_template.json)
            filter_executed: If True, only load rows where Executed='Yes'
            module_filter: Optional - only return data for specific module/SP name
            
        Returns:
            Transformed test data dictionary ready for execution
            
        Example:
            data = TemplateTransformer.load_and_transform(
                'keyword_driven_tests.csv',
                template_file='data_layer/test_data/usp_CreateUpdateSchedulingTeam/generic_template.json',
                filter_executed=True,
                module_filter='usp_CreateUpdateSchedulingTeam'
            )
        """
        if template_file is None:
            template_file = 'data_layer/test_data/generic_template.json'
        
        logger.info(f"CSV Reference File: {os.path.abspath(csv_file) if os.path.exists(csv_file) else csv_file}")
        logger.info(f"Template Reference File: {os.path.abspath(template_file) if os.path.exists(template_file) else template_file}")
        if os.path.exists(template_file):
            logger.info(f"  File size: {os.path.getsize(template_file)} bytes")
        if module_filter:
            logger.info(f"Filtering to module: {module_filter}")
        
        # Load CSV data using keyword-driven loader
        csv_data = DataLoaderFactory.load(csv_file, loader_type='keyword_driven')
        
        # Load template
        with open(template_file, 'r', encoding='utf-8') as f:
            template = json.load(f)
        
        logger.info(f"Loaded template with {len(template)} modules\n")
        
        # Transform and populate
        transformed_data = {}
        
        for module_name, test_cases in csv_data.items():
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
                
                # Populate template with CSV values
                populated_case = TemplateTransformer._populate_template(
                    template.get(module_name, [{}])[0] if module_name in template else {},
                    test_case
                )
                
                populated_case['Module'] = test_case.get('operation', module_name)
                populated_case['Operation'] = test_case.get('operation', '')
                populated_case['Test Case ID'] = test_case.get('case_id', '')
                
                transformed_cases.append(populated_case)
                logger.debug(f"Populated test case: {test_case.get('case_id')}")
            
            if transformed_cases:
                transformed_data[module_name] = transformed_cases
                logger.info(f"Module {module_name}: {len(transformed_cases)} test cases")
        
        logger.info(f"Transformation complete: {sum(len(v) for v in transformed_data.values())} total test cases")
        return transformed_data
    
    @staticmethod
    def _populate_template(template: Dict[str, Any], csv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Populate template with CSV data values.
        
        Args:
            template: Template dictionary with placeholders
            csv_data: CSV row data with actual values
            
        Returns:
            Populated template with values from CSV
        """
        import copy
        
        # Deep copy to avoid modifying original
        result = copy.deepcopy(template)
        
        # Get parameters from CSV
        params = csv_data.get('parameters', {})
        
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
        'data_layer/test_data/keyword_driven_tests.csv',
        filter_executed=True
    )
    print(json.dumps(data, indent=2))
