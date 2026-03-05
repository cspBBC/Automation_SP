"""Test Runner - Executes stored procedure tests."""

import json
import os
import logging
import datetime
import traceback
from typing import Dict, List, Any
from config.config import DataConfig
from test_engine_layer.template_transformer import TemplateTransformer

from data_loader_factory import TestDataLoader
from database_layer.connection import DBSession, get_connection
from database_layer.procedure_executor import run_stored_procedure
from database_layer.chain_executor import SPChainExecutor
from test_engine_layer.utils import Colors, setup_logging
from test_engine_layer.parameter_manager import format_dict, make_context
from test_engine_layer.builder import build_test_context, get_column_names

logger = logging.getLogger('sp_validation')


def _execute_single_test(sp_name: str, parameters: Dict, logger=None):
    """Execute a single SP test."""
    if logger is None:
        logger = logging.getLogger('sp_validation')
    
    logger.info(f"Executing {sp_name} (single)...")
    
    result = run_stored_procedure(sp_name, parameters)
    
    if result:
        logger.info(f"[OK] Results ({len(result)} rows):")
        for row_idx, row in enumerate(result, 1):
            logger.info(f"    Row {row_idx}: {row}")
    else:
        logger.info("[OK] No results returned (expected if SP has no SELECT output)")


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
    if logger is None:
        logger = logging.getLogger('sp_validation')
    
    def _log_msg(msg):
        logger.info(msg)
    
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
    if logger is None:
        logger = logging.getLogger('sp_validation')
    
    def _log_msg(msg):
        logger.info(msg)
    
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
        data_file: Name of data file to support any format (CSV/XLSX/XLS/JSON). If None, defaults to config.DataConfig.DEFAULT_TEST_DATA_FILE
                  Format auto-detected from extension. Examples:
                  - DataConfig.DEFAULT_TEST_DATA_FILE (configured default)
                  - 'custom_tests.xlsx' (Excel format)
                  - 'test_data.json' (JSON format)
    
    Returns:
        Result summary dictionary with all test results
        
    Examples:
        # No arguments - uses default CSV
        result = run_stored_procedures_from_data()
        
        # Use Excel file instead
        result = run_stored_procedures_from_data(data_file='custom_tests.xlsx')
        
        # Run specific test case in CSV
        result = run_stored_procedures_from_data(filter_test_name='Create_New_Schd_Team_01')
        
        # Run specific test case in Excel
        result = run_stored_procedures_from_data(data_file='custom_tests.xlsx', filter_test_name='Create_New_Schd_Team_01')
    """
    
    
    # Default to configured data file if not specified
    if data_file is None:
        data_file = DataConfig.DEFAULT_TEST_DATA_FILE
    
    logger = setup_logging()
    logger.info(f"\n{'='*90}")
    logger.info(f"Auto-Discovery Test Data-Driven Execution: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Data File: {data_file}")
    logger.info(f"Filter Executed: {filter_executed}")
    logger.info(f"{'='*90}\n")
    
    try:
        # Step 1: Find and load test data from default location (format auto-detected)
        data_filename = data_file  # Loader handles path resolution
        
        # Check root level first, then fall back to nested path
        root_path = os.path.abspath(data_file)
        nested_path = os.path.join('data_layer', 'test_data', data_file)
        
        # Determine which path to use
        if os.path.exists(root_path):
            data_path = root_path
        elif os.path.exists(nested_path):
            data_path = nested_path
        else:
            logger.error(f"Data file not found: {root_path} or {nested_path}")
            return {'error': f'Data file not found: {root_path} or {nested_path}'}
        
        logger.info(f"Data File Path: {os.path.abspath(data_path)}")
        logger.info(f"File exists: True")
        logger.info(f"File size: {os.path.getsize(data_path)} bytes\n")
        
        # Step 2: Load test data (format auto-detected from extension: CSV, XLSX, XLS, JSON)
        # Pass just the filename - loader adds data_layer/test_data/ prefix and auto-detects format
        
        # For keyword-driven format, use appropriate loader based on file extension
        file_ext = os.path.splitext(data_file)[1].lower()
        
        if file_ext in ['.csv', '']:
            # CSV or no extension - use keyword-driven CSV loader
            test_data = TestDataLoader.load(data_filename)
        elif file_ext in ['.xlsx', '.xls']:
            # Excel format - auto-detects and uses Excel loader
            logger.info("Loading test data from Excel format")
            test_data = TestDataLoader.load(data_filename)
        else:
            # Other formats - auto-detect format
            logger.info(f"Loading test data from {file_ext} format")
            test_data = TestDataLoader.load(data_filename)
        
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
                # search order: data_layer/test_data/<module>/template_data/<module>_<op>.json -> legacy paths
                test_data_base = 'data_layer/test_data'
                module_template_dir = os.path.join(test_data_base, module_name, 'template_data')
                specific_template = None

                candidate_paths = []
                # New modularized structure: data_layer/test_data/{module}/template_data/
                if os.path.isdir(module_template_dir):
                    candidate_paths.append(os.path.join(module_template_dir, f"{module_name}_{op}.json"))
                # Legacy paths for backward compatibility
                candidate_paths.append(os.path.join(test_data_base, 'modules', module_name, f"{module_name}_{op}.json"))
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
        logger.error(f"Test data-driven execution failed: {e}")
        logger.error(traceback.format_exc())
        return {'error': str(e)}


# Backward compatibility alias
# Old code using run_stored_procedures_from_csv() will still work
run_stored_procedures_from_csv = run_stored_procedures_from_data