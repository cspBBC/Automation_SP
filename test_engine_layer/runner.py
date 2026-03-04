"""Test Runner - Executes stored procedure tests."""

import json
import os
import logging
import datetime
import traceback
from typing import Dict, List, Any
from test_engine_layer.template_transformer import TemplateTransformer

from data_loader_factory import DataLoaderFactory
from database_layer.connection import DBSession, get_connection
from database_layer.procedure_executor import run_stored_procedure
from database_layer.chain_executor import SPChainExecutor
from test_engine_layer.utils import Colors, setup_logging
from test_engine_layer.parameter_manager import format_dict, make_context
from test_engine_layer.builder import build_test_context, get_column_names

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
        msg = f"[OK] Results ({len(result)} rows):"
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
        msg = "[OK] No results returned (expected if SP has no SELECT output)"
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


def run_stored_procedures_from_data(filter_executed: bool = True, filter_test_name: str = None, data_file: str = None) -> Dict[str, Any]:
    """Auto-discovery scaffold framework for test data-driven test execution.
    
    Supports CSV, Excel (XLSX/XLS) and other formats. Format is auto-detected from file extension.
    
    Pattern:
    1. Automatically reads data_layer/test_data/{data_file} (CSV/XLSX/XLS auto-detected)
    2. Extracts unique module names (SPs) from test data
    3. For each module, identifies operations requested
    4. For each operation attempts to load an operation-specific JSON template
       (ordered lookup: modules/<module>/<module>_<op>.json,
        data_layer/test_data/<module>_<op>.json, or generic <module>.json)
    5. Executes test cases based on test data contents
    
    Args:
        filter_executed: If True, only run rows where Executed='Yes' (default: True)
        filter_test_name: If provided, only run the test case with this name (for independent test execution)
        data_file: Name of data file to support any format (CSV/XLSX/XLS/JSON). If None, defaults to 'keyword_driven_tests.csv'
                  Format auto-detected from extension. Examples:
                  - 'keyword_driven_tests.csv' (default)
                  - 'keyword_driven_tests.xlsx' (Excel format)
                  - 'test_data' (assumes .json)
    
    Returns:
        Result summary dictionary with all test results
        
    Examples:
        # No arguments - uses default CSV
        result = run_stored_procedures_from_data()
        
        # Use Excel file instead
        result = run_stored_procedures_from_data(data_file='keyword_driven_tests.xlsx')
        
        # Run specific test case in CSV
        result = run_stored_procedures_from_data(filter_test_name='Create_New_Schd_Team_01')
        
        # Run specific test case in Excel
        result = run_stored_procedures_from_data(data_file='keyword_driven_tests.xlsx', filter_test_name='Create_New_Schd_Team_01')
    """
    
    
    # Default to CSV if not specified
    if data_file is None:
        data_file = 'keyword_driven_tests.csv'
    
    logger = setup_logging()
    logger.info(f"\n{'='*90}")
    logger.info(f"Auto-Discovery Test Data-Driven Execution: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Data File: {data_file}")
    logger.info(f"Filter Executed: {filter_executed}")
    logger.info(f"{'='*90}\n")
    
    try:
        # Step 1: Find and load test data from default location (format auto-detected)
        data_filename = data_file  # Loader adds data_layer/test_data/ prefix and auto-detects format
        data_path = os.path.join('data_layer', 'test_data', data_file)
        
        if not os.path.exists(data_path):
            logger.error(f"Data file not found: {data_path}")
            return {'error': f'Data file not found: {data_path}'}
        
        logger.info(f"Data File Path: {os.path.abspath(data_path)}")
        logger.info(f"File exists: True")
        logger.info(f"File size: {os.path.getsize(data_path)} bytes\n")
        
        # Step 2: Load test data (format auto-detected from extension: CSV, XLSX, XLS, JSON)
        # Pass just the filename - loader adds data_layer/test_data/ prefix and auto-detects format
        
        # For keyword-driven format, use appropriate loader based on file extension
        file_ext = os.path.splitext(data_file)[1].lower()
        
        if file_ext in ['.csv', '']:
            # CSV or no extension - use keyword-driven CSV loader
            test_data = DataLoaderFactory.load(data_filename, loader_type='keyword_driven')
        elif file_ext in ['.xlsx', '.xls']:
            # Excel format - use ExcelLoader (note: must have keyword-driven structure)
            logger.info("Loading keyword-driven data from Excel format")
            test_data = DataLoaderFactory.load(data_filename)  # Auto-detects Excel format
        else:
            # Other formats - try factory
            logger.info(f"Loading keyword-driven data from {file_ext} format")
            test_data = DataLoaderFactory.load(data_filename)
        
        if not test_data:
            logger.warning("No test data loaded from data file")
            return {}
        
        # Extract unique module names from test data
        unique_modules = list(test_data.keys())
        logger.info(f"Discovered {len(unique_modules)} unique module(s) in data file: {unique_modules}\n")
        
        if filter_test_name:
            logger.info(f"Running specific test case: {filter_test_name}\n")
        
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
            # Collect all requested operations for this module (respecting executed flag and test name filter)
            module_rows = test_data.get(module_name, [])
            ops = set()
            for row in module_rows:
                if filter_executed and not row.get('executed', False):
                    continue
                # If specific test_name filter provided, only include matching rows
                if filter_test_name and row.get('case_id') != filter_test_name:
                    continue
                op = row.get('operation')
                if op:
                    ops.add(op)
            if not ops:
                logger.info(f"No executable operations found for module {module_name}, skipping")
                continue

            logger.info(f"Module: {module_name} (operations: {sorted(ops)})")
            test_cases = []

            # For each operation, try to load an operation-specific template first
            for op in sorted(ops):
                # search order: modules/<module>/<module>_<op>.json -> data_layer/test_data/<module>_<op>.json -> data_layer/test_data/<module>.json
                test_data_base = 'data_layer/test_data'
                module_folder = os.path.join(test_data_base, 'modules', module_name)
                specific_template = None

                candidate_paths = []
                if os.path.isdir(module_folder):
                    candidate_paths.append(os.path.join(module_folder, f"{module_name}_{op}.json"))
                candidate_paths.append(os.path.join(test_data_base, f"{module_name}_{op}.json"))
                candidate_paths.append(os.path.join(test_data_base, f"{module_name}.json"))

                for path in candidate_paths:
                    if os.path.exists(path):
                        specific_template = path
                        break

                if not specific_template:
                    logger.warning(f"Template not found for {module_name} operation {op} (looked in {candidate_paths})")
                    continue

                logger.info(f"  Using template: {os.path.abspath(specific_template)}")

                # Step 4: Transform test data using discovered template
                test_data_for_op = TemplateTransformer.load_and_transform(
                    data_filename,
                    template_file=specific_template,
                    filter_executed=filter_executed,
                    module_filter=module_name,
                    filter_test_name=filter_test_name
                )

                if not test_data_for_op or module_name not in test_data_for_op:
                    logger.info(f"    No test cases after filtering for {module_name} / {op}")
                    continue

                # pick only cases belonging to this operation (load_and_transform sets Operation key)
                op_cases = [c for c in test_data_for_op[module_name] if c.get('Operation') == op]
                logger.info(f"    Loaded {len(op_cases)} case(s) for operation {op}")
                test_cases.extend(op_cases)

            if not test_cases:
                logger.info(f"  No test cases collected for module {module_name}")
                continue

            logger.info(f"  Total test cases to execute: {len(test_cases)}\n")
            
            # Step 5: Execute test cases with execution context chaining
            module_results = []
            execution_context = {}  # Track outputs from Create for injection into Edit
            
            for test_case in test_cases:
                case_id = test_case.get('Test Case ID', 'unknown')
                logger.info(f"  Executing: {case_id}")
                
                # Inject execution context values into test_case parameters before execution
                if execution_context and 'chain_config' in test_case:
                    chain_config = test_case['chain_config']
                    if isinstance(chain_config, list):
                        for step in chain_config:
                            # Inject context into step parameters (used for input_mappings)
                            step['_execution_context'] = execution_context
                
                try:
                    if 'chain_config' in test_case and test_case['chain_config']:
                        executor = SPChainExecutor(connection)
                        result = executor.execute_chain(test_case['chain_config'], execution_context=execution_context)
                        
                        # Extract execution context from result if available (for chaining operations)
                        if isinstance(result, dict):
                            if result.get('chain_data'):
                                execution_context.update(result.get('chain_data', {}))
                                logger.info(f"    Updated execution_context with: {result.get('chain_data', {})}")
                        
                        # Respect executor result status: mark failed when chain reports failure
                        if isinstance(result, dict) and not result.get('success', True):
                            module_results.append({
                                'case_id': case_id,
                                'Operation': test_case.get('Operation'),
                                'status': 'FAILED',
                                'error': result.get('error'),
                                'result': result,
                                'execution_context': execution_context.copy()
                            })
                        else:
                            module_results.append({
                                'case_id': case_id,
                                'Operation': test_case.get('Operation'),
                                'status': 'PASSED',
                                'result': result,
                                'execution_context': execution_context.copy()
                            })
                    else:
                        logger.warning(f"    No chain_config for {case_id}")
                        module_results.append({
                            'case_id': case_id,
                            'Operation': test_case.get('Operation'),
                            'status': 'SKIPPED',
                            'error': 'No chain_config'
                        })
                
                except Exception as e:
                    logger.error(f"    Failed: {e}")
                    module_results.append({
                        'case_id': case_id,
                        'Operation': test_case.get('Operation'),
                        'status': 'FAILED',
                        'error': str(e)
                    })
            
            all_results[module_name] = module_results
        
        # Summary
        total = sum(len(v) for v in all_results.values())
        passed = sum(1 for results in all_results.values() for r in results if r.get('status') == 'PASSED')
        failed = sum(1 for results in all_results.values() for r in results if r.get('status') == 'FAILED')
        skipped = sum(1 for results in all_results.values() for r in results if r.get('status') == 'SKIPPED')
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Test Execution Summary:")
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


# Backward compatibility alias
# Old code using run_stored_procedures_from_csv() will still work
run_stored_procedures_from_csv = run_stored_procedures_from_data