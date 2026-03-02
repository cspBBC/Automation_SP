"""Test Runner - Executes stored procedure tests."""

import json
import os
import logging
import datetime
import traceback
from typing import Dict, List, Any

from data_loader_factory import DataLoaderFactory
from database_layer.connection import DBSession, get_connection
from database_layer.procedure_executor import run_stored_procedure
from database_layer.chain_executor import SPChainExecutor
from test_engine_layer.utils import Colors, setup_logging
from test_engine_layer.parameter_manager import format_dict, make_context
from test_engine_layer.builder import build_test_context, get_column_names
from test_engine_layer.enums import TestCaseType

logger = logging.getLogger(__name__)


def load_test_inputs(test_inputs: str) -> Dict[str, Any]:
    """Load test inputs from JSON file.
    
    Args:
        test_inputs: Filename without extension (e.g., 'createSchdGroup_testData')
                    
    Returns:
        Test data dictionary keyed by SP name
    """
    return DataLoaderFactory.load(test_inputs, format='json')


def run_stored_procedures(sp_name: str, case_type=None, test_inputs: str = None) -> Dict[str, Any]:
    """Run test cases from JSON matching the given stored procedure name.
    
    Args:
        sp_name: Name of the stored procedure
        case_type: TestCaseType enum member (POSITIVE, NEGATIVE, EDGE) or string
        test_inputs: Filename without extension (mandatory)
    
    Returns:
        Result summary dictionary
    """
    logger = setup_logging()
    logger.info(f"\n{'='*90}")
    logger.info(f"Test Execution Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"SP Name: {sp_name}")
    logger.info(f"Test Inputs: {test_inputs}")
    logger.info(f"{'='*90}\n")
    
    # Load test data
    test_data = load_test_inputs(test_inputs)
    
    if sp_name not in test_data:
        filename = test_inputs
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        logger.info(f"No test cases found for SP '{sp_name}' in {filename}")
        return {}
    
    test_cases = test_data[sp_name]
    
    # Filter by case type if provided
    if case_type:
        try:
            normalized = case_type.name.upper()
        except Exception:
            normalized = str(case_type).upper()
        
        test_cases = [tc for tc in test_cases 
                     if tc.get('case_type', '').upper() == normalized]
        
        if not test_cases:
            logger.info(f"No '{normalized}' test cases found for SP '{sp_name}'")
            return {}
    
    logger.info(f"Found {len(test_cases)} test case(s) for {sp_name}\n")
    
    # Track test results
    test_results = []
    
    for idx, test_case in enumerate(test_cases, 1):
        case_id = test_case.get('case_id', f'case_{idx}')
        case_type_label = test_case.get('case_type', 'unknown')
        description = test_case.get('description', '')
        
        logger.info(f"{'='*80}")
        logger.info(f"[{idx}/{len(test_cases)}] Case: {case_id}")
        logger.info(f"Type: {case_type_label}")
        logger.info(f"Description: {description}")
        logger.info(f"{'='*80}")
        
        case_passed = True
        case_chain_data = {}
        
        try:
            # Create initial context
            base_params = test_case.get('parameters', {}) or {}
            ctx = build_test_context(base_params)
            
            # Run pre-SQL statements
            if test_case.get('pre_sql'):
                _run_sql_list(test_case['pre_sql'], label="PRE", context=ctx, logger=logger)
            
            # Detect if this is chained or single execution
            chain_result = None
            if 'chain_config' in test_case:
                chain_result = _execute_chain_test(test_case['chain_config'], context=ctx, logger=logger)
                if chain_result and chain_result.get('chain_data'):
                    case_chain_data = chain_result.get('chain_data', {})
            else:
                parameters = test_case.get('parameters', {})
                parameters = format_dict(parameters, ctx)
                _execute_single_test(sp_name, parameters, logger=logger)
            
            # Build validation context
            if 'chain_config' in test_case:
                first_step = test_case['chain_config'][0]
                params = first_step.get('parameters', {})
            else:
                params = test_case.get('parameters', {})
            
            ctx_validation = make_context(params, chain_data=(chain_result or {}).get('chain_data'))
            ctx_validation.update(ctx)
            
            # Execute post-SQL
            if test_case.get('post_sql'):
                post_results = _run_sql_list(test_case['post_sql'], label="POST", context=ctx_validation, logger=logger)
                
                # Validate against expected post-state
                if test_case.get('expected_post_state'):
                    from validation_layer.result_validator import validate_post_state
                    validation_passed = validate_post_state(post_results, test_case['expected_post_state'], ctx_validation, logger=logger)
                    if not validation_passed:
                        case_passed = False
            
            # Execute cleanup SQL
            if test_case.get('cleanup_sql'):
                _run_sql_list(test_case['cleanup_sql'], label="CLEANUP", context=ctx_validation, logger=logger)
        
        except Exception as e:
            error_msg = f"Error: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            case_passed = False
        
        # Record test result
        test_results.append({
            'case_id': case_id,
            'case_type': case_type_label,
            'passed': case_passed,
            'chain_data': case_chain_data,
            'context': ctx
        })
    
    # Log completion
    separator = f"\n{'='*90}\n"
    logger.info(f"\n{'='*90}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*90}")
    
    passed_count = sum(1 for r in test_results if r['passed'])
    failed_count = len(test_results) - passed_count
    
    for result in test_results:
        status_clean = "[PASS]" if result['passed'] else "[FAIL]"
        msg = f"  {status_clean}  {result['case_id']} ({result['case_type']})"
        logger.info(msg)
    
    logger.info(f"\nTotal: {len(test_results)} | Passed: {passed_count} | Failed: {failed_count}")
    logger.info(f"{'='*90}\n")
    
    logger.info(separator)
    logger.info(f"Test Execution Completed: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(separator)
    
    # Return results summary
    result_summary = {
        'success': all(r['passed'] for r in test_results),
        'passed_count': passed_count,
        'failed_count': failed_count,
        'test_results': test_results,
        'total_tests': len(test_results)
    }
    
    if test_results and test_results[0].get('chain_data'):
        result_summary['chain_data'] = test_results[0]['chain_data']
        result_summary['created_team_id'] = test_results[0]['chain_data'].get('created_team_id')
        result_summary['generated_team_name'] = test_results[0]['chain_data'].get('generated_team_name')
    
    if test_results and test_results[0].get('context'):
        result_summary['context'] = test_results[0]['context']
    
    return result_summary


def _execute_single_test(sp_name: str, parameters: Dict, logger=None):
    """Execute a single SP test."""
    msg = f"Executing {sp_name} (single)..."
    if logger:
        logger.info(msg)
    else:
        print(msg)
    
    result = run_stored_procedure(sp_name, parameters)
    
    if result:
        msg = f"✓ Results ({len(result)} rows):"
        if logger:
            logger.info(msg)
        else:
            print(msg)
        for row_idx, row in enumerate(result, 1):
            msg = f"    Row {row_idx}: {row}"
            if logger:
                logger.info(msg)
            else:
                print(msg)
    else:
        msg = "✓ No results returned (OK if SP has no SELECT output)"
        if logger:
            logger.info(msg)
        else:
            print(msg)


def _run_sql_list(sql_list: List, label: str = "", context: Dict = None, logger=None) -> List:
    """Helper to execute a list of SQL statements.
    
    Args:
        sql_list: List of SQL strings or (sql, params) tuples
        label: Optional prefix for logs
        context: Dict for string formatting
        logger: Optional logger
        
    Returns:
        List of (result_rows, col_names) tuples
    """
    context = context or {}
    
    def _log_msg(msg):
        if logger:
            logger.info(msg)
        else:
            print(msg)
    
    _log_msg(f"\n-- {label} SQL statements --")
    all_results = []
    
    with DBSession() as db:
        for entry in sql_list:
            if isinstance(entry, (list, tuple)) and len(entry) == 2:
                sql, params = entry
            else:
                sql, params = entry, []
            
            # Apply context formatting
            try:
                formatted = sql.format(**context)
            except Exception:
                formatted = sql
            
            _log_msg(f"SQL: {formatted}")
            
            try:
                sql_upper = formatted.strip().upper()
                is_query = sql_upper.startswith('SELECT')
                
                if is_query:
                    db.cursor.execute(formatted, params or [])
                    rows = db.cursor.fetchall()
                    
                    col_names = []
                    try:
                        if db.cursor.description:
                            col_names = [desc[0] for desc in db.cursor.description]
                    except Exception:
                        pass
                    
                    all_results.append((rows, col_names))
                    
                    if rows:
                        for r in rows:
                            _log_msg(f"    {r}")
                    else:
                        _log_msg("    -- no rows returned --")
                else:
                    try:
                        db.cursor.execute(formatted, params or [])
                        affected_rows = db.cursor.rowcount
                        all_results.append((affected_rows, None))
                        _log_msg(f"    -- {affected_rows} row(s) affected --")
                    except Exception as dml_err:
                        _log_msg(f"    ERROR executing as DML: {dml_err}")
                        all_results.append((None, None))
            except Exception as e:
                _log_msg(f"    ERROR executing statement: {e}")
                all_results.append((None, None))
    
    _log_msg(f"-- end {label} SQL --\n")
    return all_results


def _execute_chain_test(chain_config: List[Dict], context: Dict = None, logger=None) -> Dict:
    """Execute a chained SP test.
    
    Args:
        chain_config: List of chain step configurations
        context: Execution context
        logger: Optional logger
        
    Returns:
        Result dictionary
    """
    def _log_msg(msg):
        if logger:
            logger.info(msg)
        else:
            print(msg)
    
    import copy
    context = context or {}
    formatted_chain = []
    
    for step in chain_config:
        step_copy = copy.deepcopy(step)
        params = step_copy.get('parameters', {})
        step_copy['parameters'] = format_dict(params, context)
        formatted_chain.append(step_copy)
    
    connection = get_connection()
    
    try:
        executor = SPChainExecutor(connection)
        executor.set_logger(_log_msg)
        result = executor.execute_chain(formatted_chain)
        
        if result['success']:
            _log_msg(f"\n{Colors.success('[SUCCESS]')} Chain execution completed successfully!")
            _log_msg(f"\nChain data (extracted/passed between steps):")
            if result.get('chain_data'):
                for key, value in result['chain_data'].items():
                    _log_msg(f"  {key}: {value}")
            else:
                _log_msg("  (no data extracted)")
        else:
            _log_msg(f"\n{Colors.fail('[FAILED]')} CHAIN EXECUTION FAILED")
            _log_msg(f"{'='*80}")
            
            if result.get('failed_step'):
                _log_msg(f"{Colors.fail('Failed at:')} STEP {result['failed_step']}")
            
            _log_msg(f"\n{Colors.fail('Error:')} {result.get('error')}")
            
            if result.get('partial_results'):
                _log_msg(f"\nPartial results (steps completed before failure):")
                for step_key, step_result in result['partial_results'].items():
                    _log_msg(f"\n  {step_key}:")
                    if isinstance(step_result, dict) and 'rows' in step_result:
                        for row in step_result['rows']:
                            row_list = list(row) if hasattr(row, '__getitem__') else [row]
                            if len(row_list) >= 2:
                                status = row_list[0]
                                message = row_list[1]
                                status_icon = "[OK]" if status == 1 else "[FAIL]"
                                _log_msg(f"    {status_icon} Status: {status}")
                                _log_msg(f"    {message}")
            
            if result.get('chain_data'):
                _log_msg(f"\nChain data collected before failure:")
                for key, value in result['chain_data'].items():
                    _log_msg(f"  {key}: {value}")
            
            _log_msg(f"{'='*80}")
        
        return result
    finally:
        if connection:
            connection.close()


def run_stored_procedures_from_csv(filter_executed: bool = True) -> Dict[str, Any]:
    """Auto-discovery scaffold framework for CSV-driven test execution.
    
    No arguments needed - everything comes from CSV!
    
    Scaffold Pattern:
    1. Automatically reads data_layer/test_data/keyword_driven_tests.csv
    2. Extracts unique module names (SPs) from CSV
    3. For each module, searches for matching folder in test data
    4. Loads template from {module_folder}/generic_template.json
    5. Executes test cases based on CSV contents
    
    Args:
        filter_executed: If True, only run rows where Executed='Yes' (default: True)
    
    Returns:
        Result summary dictionary with all test results
        
    Example:
        # No arguments - everything auto-discovered from CSV
        result = run_stored_procedures_from_csv()
        
        # Or filter to executed tests only (default)
        result = run_stored_procedures_from_csv(filter_executed=True)
    """
    from test_engine_layer.template_transformer import TemplateTransformer
    
    logger = setup_logging()
    logger.info(f"\n{'='*90}")
    logger.info(f"Auto-Discovery CSV Test Execution (Scaffold): {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Filter Executed: {filter_executed}")
    logger.info(f"{'='*90}\n")
    
    try:
        # Step 1: Find and load CSV from default location
        csv_filename = 'keyword_driven_tests.csv'  # Loader adds data_layer/test_data/ prefix
        csv_path = 'data_layer/test_data/keyword_driven_tests.csv'
        
        if not os.path.exists(csv_path):
            logger.error(f"CSV not found: {csv_path}")
            return {'error': f'CSV file not found: {csv_path}'}
        
        logger.info(f"CSV File: {csv_path}")
        
        # Step 2: Load CSV to identify unique modules
        # Pass just the filename - loader adds data_layer/test_data/ prefix automatically
        csv_data = DataLoaderFactory.load(csv_filename, loader_type='keyword_driven')
        
        if not csv_data:
            logger.warning("No data loaded from CSV")
            return {}
        
        # Extract unique module names from CSV
        unique_modules = list(csv_data.keys())
        logger.info(f"Discovered {len(unique_modules)} unique module(s) in CSV: {unique_modules}\n")
        
        # Step 3: For each module, find its folder and template
        all_results = {}
        # Prefer any test transaction connection (set by pytest fixture) to avoid committing
        from database_layer.transaction_manager import get_test_transaction
        test_tx = get_test_transaction()
        if test_tx:
            connection = test_tx
            logger.info("Using test transaction connection (will be rolled back by fixture)")
        else:
            connection = get_connection()
        
        for module_name in unique_modules:
            # Search for module-specific template file: {module_name}.json
            test_data_base = 'data_layer/test_data'
            template_file = os.path.join(test_data_base, f"{module_name}.json")
            
            # Verify template exists
            if not os.path.exists(template_file):
                logger.warning(f"Template not found: {template_file}")
                logger.info(f"  Skipping module: {module_name}")
                continue
            
            logger.info(f"Module: {module_name}")
            logger.info(f"  Template: {template_file}")
            
            # Step 4: Transform CSV data using discovered template
            test_data_for_module = TemplateTransformer.load_and_transform(
                csv_filename,  # Just filename - loader adds prefix
                template_file=template_file,
                filter_executed=filter_executed,
                module_filter=module_name  # Only this module
            )
            
            if not test_data_for_module or module_name not in test_data_for_module:
                logger.info(f"  No test cases after filtering for {module_name}")
                continue
            
            test_cases = test_data_for_module[module_name]
            logger.info(f"  Loaded {len(test_cases)} test case(s)\n")
            
            # Step 5: Execute test cases
            module_results = []
            for test_case in test_cases:
                case_id = test_case.get('Test Case ID', 'unknown')
                logger.info(f"  Executing: {case_id}")
                
                try:
                    if 'chain_config' in test_case and test_case['chain_config']:
                        executor = SPChainExecutor(connection)
                        result = executor.execute_chain(test_case['chain_config'])
                        # Respect executor result status: mark failed when chain reports failure
                        if isinstance(result, dict) and not result.get('success', True):
                            module_results.append({
                                'case_id': case_id,
                                'status': 'failed',
                                'error': result.get('error'),
                                'result': result
                            })
                        else:
                            module_results.append({
                                'case_id': case_id,
                                'status': 'passed',
                                'result': result
                            })
                    else:
                        logger.warning(f"    No chain_config for {case_id}")
                        module_results.append({
                            'case_id': case_id,
                            'status': 'skipped',
                            'error': 'No chain_config'
                        })
                
                except Exception as e:
                    logger.error(f"    Failed: {e}")
                    module_results.append({
                        'case_id': case_id,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            all_results[module_name] = module_results
        
        # Summary
        total = sum(len(v) for v in all_results.values())
        passed = sum(1 for results in all_results.values() for r in results if r.get('status') == 'passed')
        failed = sum(1 for results in all_results.values() for r in results if r.get('status') == 'failed')
        skipped = sum(1 for results in all_results.values() for r in results if r.get('status') == 'skipped')
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Scaffold Execution Summary:")
        logger.info(f"  Total: {total}, Passed: {passed}, Failed: {failed}, Skipped: {skipped}")
        logger.info(f"{'='*80}\n")
        
        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'results': all_results
        }
    
    except Exception as e:
        logger.error(f"Scaffold CSV execution failed: {e}")
        logger.error(traceback.format_exc())
        return {'error': str(e)}

