import json
import os
import logging
from core.db.procedures import run_stored_procedure
from core.db.sp_chain_executor import SPChainExecutor



def load_test_inputs(test_inputs):
    """Load test inputs from JSON file in tests/test_data folder.
    
    Args:
        test_inputs: Filename without extension (e.g., 'users_tests', 'shekjar', 'schgrp_fta').
                    MANDATORY - must be provided.
                    Function automatically appends .json extension.
    """
    if not test_inputs:
        raise ValueError("test_inputs filename is mandatory")
    base = os.path.dirname(os.path.dirname(__file__))
    filename = test_inputs
    # Automatically append .json if not present
    if not filename.endswith('.json'):
        filename = f"{filename}.json"
    test_file = os.path.join(base, 'test_data', filename)
    
    if not os.path.exists(test_file):
        raise FileNotFoundError(f"Test input file not found: {test_file}")
    
    with open(test_file, 'r') as f:
        return json.load(f)


def configure_logging():
    """Configure logging to output to console and file"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('tests/test_output.log'),
            logging.StreamHandler()
        ]
    )


def test_stored_procedures(sp_name, case_type=None, test_inputs=None):
    """
    Run test cases from JSON matching the given stored procedure name.
    
    Args:
        sp_name: Name of the stored procedure (e.g., 'usp_CreateUpdateSchedulingTeam')
        case_type: TestCaseType enum member (POSITIVE, NEGATIVE, EDGE) or string
        test_inputs: Filename without extension (e.g., 'users_tests', 'shekjar', 'schgrp_fta').
                    MANDATORY - must be provided.
                    Function automatically appends .json extension.
                    Files always located under tests/test_data/.
    
    Supports both:
    - Single SP execution (uses run_stored_procedure)
    - Chained SP execution (uses SPChainExecutor) when chain_config present
    
    Example usage:
        # Use custom JSON file (tests/test_data/users_tests.json)
        test_stored_procedures('usp_GetUsers', TestCaseType.POSITIVE, 
                             test_inputs='users_tests')
        
        # Use shekjar.json
        test_stored_procedures('usp_GetUsers', TestCaseType.POSITIVE, 
                             test_inputs='shekjar')
    """
    test_data = load_test_inputs(test_inputs)
    
    # Handle new JSON structure (SP name as key)
    if sp_name not in test_data:
        filename = test_inputs
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        print(f"No test cases found for SP '{sp_name}' in {filename}")
        return
    
    test_cases = test_data[sp_name]
    
    # Filter by case type if provided
    if case_type:
        try:
            # Enum members have a 'name' attribute
            normalized = case_type.name.upper()
        except Exception:
            # fall back to string conversion
            normalized = str(case_type).upper()
        
        test_cases = [tc for tc in test_cases 
                     if tc.get('case_type', '').upper() == normalized]
        
        if not test_cases:
            print(f"No '{normalized}' test cases found for SP '{sp_name}'")
            return
    
    print(f"\nFound {len(test_cases)} test case(s) for {sp_name}")
    
    for idx, test_case in enumerate(test_cases, 1):
        case_id = test_case.get('case_id', f'case_{idx}')
        case_type_label = test_case.get('case_type', 'unknown')
        description = test_case.get('description', '')
        
        print(f"\n{'='*80}")
        print(f"[{idx}/{len(test_cases)}] Case: {case_id}")
        print(f"Type: {case_type_label}")
        print(f"Description: {description}")
        print(f"{'='*80}")
        
        try:
            # Detect if this is a chained or single execution
            if 'chain_config' in test_case:
                _execute_chain_test(test_case['chain_config'])
            else:
                parameters = test_case['parameters']
                _execute_single_test(sp_name, parameters)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


def _execute_single_test(sp_name, parameters):
    """Execute a single SP test."""
    print(f"Executing {sp_name} (single)...")
    result = run_stored_procedure(sp_name, parameters)
    
    if result:
        print(f"✓ Results ({len(result)} rows):")
        for row_idx, row in enumerate(result, 1):
            print(f"    Row {row_idx}: {row}")
    else:
        print("✓ No results returned (OK if SP has no SELECT output)")


def _execute_chain_test(chain_config):
    """Execute a chained SP test."""
    print(f"Executing chained test ({len(chain_config)} steps)...")
    
    # Get database connection
    from core.db.connection import get_connection
    connection = get_connection()
    
    try:
        # Execute chain
        executor = SPChainExecutor(connection)
        result = executor.execute_chain(chain_config)
        
        if result['success']:
            print(f"\n[SUCCESS] Chain execution completed successfully!")
            print(f"\nChain data (extracted/passed between steps):")
            if result.get('chain_data'):
                for key, value in result['chain_data'].items():
                    print(f"  {key}: {value}")
            else:
                print("  (no data extracted)")
        else:
            # Failure case - show detailed error information
            print(f"\n[FAILED] CHAIN EXECUTION FAILED")
            print(f"{'='*80}")
            
            # Show which step failed
            if result.get('failed_step'):
                print(f"Failed at: STEP {result['failed_step']}")
            
            # Show error message
            print(f"\nError: {result.get('error')}")
            
            # Show partial results up to failure
            if result.get('partial_results'):
                print(f"\nPartial results (steps completed before failure):")
                for step_key, step_result in result['partial_results'].items():
                    print(f"\n  {step_key}:")
                    if isinstance(step_result, dict) and 'rows' in step_result:
                        for row in step_result['rows']:
                            row_list = list(row) if hasattr(row, '__getitem__') else [row]
                            if len(row_list) >= 2:
                                status = row_list[0]
                                message = row_list[1]
                                status_icon = "[OK]" if status == 1 else "[FAIL]"
                                print(f"    {status_icon} Status: {status}")
                                print(f"    {message}")
            
            # Show chain data available so far
            if result.get('chain_data'):
                print(f"\nChain data collected before failure:")
                for key, value in result['chain_data'].items():
                    print(f"  {key}: {value}")
            
            print(f"{'='*80}")
    finally:
        if connection:
            connection.close()