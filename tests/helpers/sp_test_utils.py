import json
import os
import logging
import datetime
import sys
from core.db.procedures import run_stored_procedure
from core.db.sp_chain_executor import SPChainExecutor

# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    @staticmethod
    def fail(text):
        """Format text as failure (red)."""
        return f"{Colors.RED}{Colors.BOLD}{text}{Colors.RESET}"
    
    @staticmethod
    def success(text):
        """Format text as success (green)."""
        return f"{Colors.GREEN}{Colors.BOLD}{text}{Colors.RESET}"
    
    @staticmethod
    def info(text):
        """Format text as info (blue)."""
        return f"{Colors.BLUE}{text}{Colors.RESET}"
    
    @staticmethod
    def warn(text):
        """Format text as warning (yellow)."""
        return f"{Colors.YELLOW}{text}{Colors.RESET}"


def _setup_logging():
    """Setup logging to both console and timestamped file.
    
    Creates output folder if needed and logs to file with datetime stamp.
    Returns the logger and file handler.
    """
    # Create output folder if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Use fixed log filename (overwrites previous execution)
    log_file = os.path.join(output_dir, 'test_run.log')
    
    # Setup logger
    logger = logging.getLogger('sp_validation')
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter('%(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, log_file


def _log(message, logger=None):
    """Print and log message to both console and file."""
    if logger:
        logger.info(message)
    else:
        print(message)



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


def _make_context(params, chain_data=None):
    """Build context dict from parameters and chain data."""
    ctx = {}
    if isinstance(params, dict):
        for k, v in params.items():
            name = k.lstrip('@')
            ctx[name] = v
    if chain_data:
        ctx.update(chain_data)
    return ctx


def _format_dict(d, ctx):
    """Return copy of dict with string values formatted using ctx."""
    if not isinstance(d, dict):
        return d
    formatted = {}
    for k, v in d.items():
        if isinstance(v, str):
            try:
                formatted[k] = v.format(**ctx)
            except Exception:
                formatted[k] = v
        elif isinstance(v, dict):
            formatted[k] = _format_dict(v, ctx)
        else:
            formatted[k] = v
    return formatted


import datetime

# Module-level cache for table column names
_column_cache = {}


def _get_column_names(table_name):
    """Get column names for a table from INFORMATION_SCHEMA (cached).
    
    Returns list of column names in ordinal order.
    """
    if table_name in _column_cache:
        return _column_cache[table_name]
    
    try:
        from core.db.connection import DBSession
        with DBSession() as db:
            # Query to get column names in order
            query = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
            """
            results = db.execute_query(query, [table_name])
            col_names = [row[0] for row in results] if results else []
            _column_cache[table_name] = col_names
            return col_names
    except Exception as e:
        return []


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
    # Setup logging to console and file
    logger, log_file = _setup_logging()
    logger.info(f"\n{'='*90}")
    logger.info(f"Test Execution Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"SP Name: {sp_name}")
    logger.info(f"Test Inputs: {test_inputs}")
    logger.info(f"Log File: {log_file}")
    logger.info(f"{'='*90}\n")
    
    test_data = load_test_inputs(test_inputs)
    
    # Handle new JSON structure (SP name as key)
    if sp_name not in test_data:
        filename = test_inputs
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        logger.info(f"No test cases found for SP '{sp_name}' in {filename}")
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
            logger.info(f"No '{normalized}' test cases found for SP '{sp_name}'")
            return
    
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
        
        case_passed = True  # Track if this test case passed
        
        try:
            # create initial context; include any supplied integer user id
            base_params = test_case.get('parameters', {}) or {}
            ctx = _make_context(base_params)
            # add dynamic values (timestamp-based name)
            ctx.setdefault('generated_team_name',
                           f"AutoTest_{datetime.datetime.now():%Y%m%d%H%M%S}")

            # run any pre‑SQL statements, if provided
            if test_case.get('pre_sql'):
                _run_sql_list(test_case['pre_sql'], label="PRE", context=ctx, logger=logger)

            # Detect if this is a chained or single execution
            chain_result = None
            if 'chain_config' in test_case:
                chain_result = _execute_chain_test(test_case['chain_config'], context=ctx, logger=logger)
            else:
                parameters = test_case['parameters']
                # format parameters using context
                parameters = _format_dict(parameters, ctx)
                _execute_single_test(sp_name, parameters, logger=logger)

            # execute verification / cleanup queries after SP call
            if test_case.get('post_sql'):
                # For chain tests, extract params from first step; for single tests use top-level params
                if 'chain_config' in test_case:
                    first_step = test_case['chain_config'][0]
                    params = first_step.get('parameters', {})
                else:
                    params = test_case.get('parameters', {})
                ctx2 = _make_context(params, chain_data=(chain_result or {}).get('chain_data'))
                # preserve any generated values
                ctx2.update(ctx)
                post_results = _run_sql_list(test_case['post_sql'], label="POST", context=ctx2, logger=logger)
                
                # Validate against expected post-state if provided
                if test_case.get('expected_post_state'):
                    validation_passed = _validate_post_state(post_results, test_case['expected_post_state'], ctx2, logger=logger)
                    if not validation_passed:
                        case_passed = False
            
            # Execute cleanup SQL if provided
            if test_case.get('cleanup_sql'):
                params = test_case.get('parameters', {})
                if 'chain_config' in test_case:
                    first_step = test_case['chain_config'][0]
                    params = first_step.get('parameters', {})
                ctx_cleanup = _make_context(params, chain_data=(chain_result or {}).get('chain_data'))
                ctx_cleanup.update(ctx)
                _run_sql_list(test_case['cleanup_sql'], label="CLEANUP", context=ctx_cleanup, logger=logger)
        except Exception as e:
            error_msg = f"Error: {e}"
            if logger:
                logger.error(error_msg)
                logger.error(traceback.format_exc())
            else:
                print(Colors.fail(error_msg))
            import traceback
            print(traceback.format_exc())
            case_passed = False
        
        # Record test result
        test_results.append({
            'case_id': case_id,
            'case_type': case_type_label,
            'passed': case_passed
        })
    
    # Log completion with colored output
    separator = f"\n{'='*90}\n"
    
    # Print test summary
    logger.info(f"\n{'='*90}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*90}")
    
    passed_count = sum(1 for r in test_results if r['passed'])
    failed_count = len(test_results) - passed_count
    
    for result in test_results:
        status = Colors.success("[PASS]") if result['passed'] else Colors.fail("[FAIL]")
        status_clean = "[PASS]" if result['passed'] else "[FAIL]"
        msg = f"  {status_clean}  {result['case_id']} ({result['case_type']})"
        logger.info(msg)
    
    logger.info(f"\nTotal: {len(test_results)} | Passed: {passed_count} | Failed: {failed_count}")
    logger.info(f"{'='*90}\n")
    
    if logger:
        # For file: plain text
        logger.info(separator)
        logger.info(f"Test Execution Completed: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(separator)
    else:
        # For console: colored
        print(separator)
        print(Colors.success(f"Test Execution Completed: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        print(separator)


def _execute_single_test(sp_name, parameters, logger=None):
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


def _run_sql_list(sql_list, label="", context=None, logger=None):
    """Helper to execute a list of SQL statements and print their output.

    Args:
        sql_list: iterable of SQL strings or (sql, params) tuples.
        label: optional prefix for logs (e.g. 'PRE', 'POST', 'CLEANUP').
        context: dict used for Python-style formatting of SQL strings.
        logger: optional logger to use instead of print.
        
    Returns:
        List of (result_rows, col_names) tuples for queries, or (affected_count, None) for DML.
    """
    from core.db.connection import DBSession
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
            # apply context formatting if needed
            try:
                formatted = sql.format(**context)
            except Exception:
                formatted = sql
            _log_msg(f"SQL: {formatted}")
            try:
                # Check if this is a SELECT query or a modification statement
                sql_upper = formatted.strip().upper()
                is_query = sql_upper.startswith('SELECT')
                
                if is_query:
                    # For SELECT statements: fetch results and column names
                    db.cursor.execute(formatted, params or [])
                    rows = db.cursor.fetchall()
                    
                    # Try to get column names from cursor description
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
                    # For DELETE/UPDATE/INSERT: just execute, don't fetch
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


def _execute_chain_test(chain_config, context=None, logger=None):
    """Execute a chained SP test.

    Returns the result dictionary so the caller can build context.
    """
    def _log_msg(msg):
        if logger:
            logger.info(msg)
        else:
            print(msg)
    
    # (header printed earlier after formatting)
    
    # apply context formatting to steps
    import copy
    context = context or {}
    formatted_chain = []
    for step in chain_config:
        step_copy = copy.deepcopy(step)
        params = step_copy.get('parameters', {})
        step_copy['parameters'] = _format_dict(params, context)
        formatted_chain.append(step_copy)

    # Get database connection
    from core.db.connection import get_connection
    connection = get_connection()
    
    try:
        # Execute chain with formatted version
        executor = SPChainExecutor(connection)
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
            # Failure case - show detailed error information
            _log_msg(f"\n{Colors.fail('[FAILED]')} CHAIN EXECUTION FAILED")
            _log_msg(f"{'='*80}")
            
            # Show which step failed
            if result.get('failed_step'):
                _log_msg(f"{Colors.fail('Failed at:')} STEP {result['failed_step']}")
            
            # Show error message
            _log_msg(f"\n{Colors.fail('Error:')} {result.get('error')}")
            
            # Show partial results up to failure
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
            
            # Show chain data available so far
            if result.get('chain_data'):
                _log_msg(f"\nChain data collected before failure:")
                for key, value in result['chain_data'].items():
                    _log_msg(f"  {key}: {value}")
            
            _log_msg(f"{'='*80}")
        return result
    finally:
        if connection:
            connection.close()


def _validate_post_state(results, expected_config, context, logger=None):
    """Validate post-SQL results against expected post-state.
    
    Args:
        results: List of (rows, col_names) tuples from _run_sql_list execution.
        expected_config: List of dicts with 'expected_columns' or 'row_count' expectations.
        context: Dict for formatting expected values.
        logger: optional logger to use instead of print.
    """
    def _log_msg(msg, use_colors=False):
        if logger:
            # Strip ANSI colors from log file
            clean_msg = msg
            for color_code in [Colors.RED, Colors.GREEN, Colors.YELLOW, Colors.BLUE, Colors.RESET, Colors.BOLD]:
                clean_msg = clean_msg.replace(color_code, '')
            # Replace Unicode checkmarks with ASCII for file logging (Windows cp1252 compatibility)
            clean_msg = clean_msg.replace('✓', '[PASS]').replace('✗', '[FAIL]')
            logger.info(clean_msg)
        else:
            print(msg)
    
    _log_msg(f"\n{'='*80}")
    _log_msg(Colors.info("VALIDATING POST-STATE"))
    _log_msg(f"{'='*80}")
    
    if not isinstance(expected_config, list):
        expected_config = [expected_config]
    
    all_pass = True
    validation_summary = []
    
    for idx, result_tuple in enumerate(results):
        _log_msg(f"\n[Query {idx + 1}] Validating result set...")
        query_pass = True
        
        # Unpack (rows, col_names) tuple
        if isinstance(result_tuple, tuple) and len(result_tuple) == 2:
            result_set, col_names = result_tuple
        else:
            # Fallback for old format
            result_set = result_tuple
            col_names = []
        
        if idx >= len(expected_config):
            _log_msg(f"  {Colors.warn('[WARN]')} (no expected_config for query {idx + 1})")
            continue
        
        expected = expected_config[idx]
        
        if result_set is None:
            msg = f"  {Colors.fail('[FAIL]')} Query execution failed (no results)"
            _log_msg(msg)
            validation_summary.append((f"Query {idx + 1}", False))
            all_pass = False
            continue
        
        # Check row count if specified
        if 'row_count' in expected:
            expected_count = expected['row_count']
            actual_count = len(result_set)
            if actual_count == expected_count:
                msg = f"  {Colors.success('[PASS]')} Row count: {actual_count} (expected {expected_count})"
                _log_msg(msg)
            else:
                msg = f"  {Colors.fail('[FAIL]')} Row count: {actual_count} (expected {expected_count})"
                _log_msg(msg)
                query_pass = False
                all_pass = False
        
        # Check specific columns if specified
        if 'expected_columns' in expected and result_set and len(result_set) > 0:
            first_row = result_set[0]
            row_dict = _row_to_dict(first_row, col_names=col_names)
            
            # Debug: show what keys we have
            if isinstance(row_dict, dict):
                available_keys = list(row_dict.keys())
                _log_msg(f"  [DEBUG] Available columns: {available_keys[:5]}...")  # show first 5
            
            expected_cols = expected['expected_columns']
            # Format expected values using context
            expected_cols = _format_dict(expected_cols, context) if isinstance(expected_cols, dict) else expected_cols
            
            for col_name, expected_val in expected_cols.items():
                # Handle case-insensitive column name matching for SQL databases
                actual_val = None
                
                if isinstance(row_dict, dict):
                    # Try exact match first
                    if col_name in row_dict:
                        actual_val = row_dict[col_name]
                    else:
                        # Try case-insensitive match
                        for key in row_dict.keys():
                            if key.lower() == col_name.lower():
                                actual_val = row_dict[key]
                                break
                
                if actual_val == expected_val:
                    msg = f"  {Colors.success('[PASS]')} {col_name}: {actual_val}"
                    _log_msg(msg)
                else:
                    msg = f"  {Colors.fail('[FAIL]')} {col_name}: {actual_val} (expected {expected_val})"
                    _log_msg(msg)
                    query_pass = False
                    all_pass = False
        
        validation_summary.append((f"Query {idx + 1}", query_pass))
    
    _log_msg(f"\n{'='*80}")
    _log_msg("VALIDATION SUMMARY")
    _log_msg(f"{'='*80}\n")
    
    for query_name, passed in validation_summary:
        if passed:
            status = Colors.success("[PASS]")
            display = f"  {status}  {query_name}"
        else:
            status = Colors.fail("[FAIL]")
            display = f"  {status}  {query_name}"
        _log_msg(display)
    
    _log_msg(f"\n{'='*80}")
    if all_pass:
        final_msg = Colors.success("ALL VALIDATIONS PASSED")
    else:
        final_msg = Colors.fail("SOME VALIDATIONS FAILED")
    _log_msg(final_msg)
    _log_msg(f"{'='*80}\n")
    return all_pass


def _row_to_dict(row, col_names=None):
    """Convert a database row (pyodbc.Row/tuple) to dict with column names as keys.
    
    Args:
        row: pyodbc.Row or tuple
        col_names: Optional list of column names. If provided, uses these to create dict.
                   If not provided, tries to use row.keys() or returns raw row.
    """
    if isinstance(row, dict):
        return row
    
    # If we have column names provided, use them to create dict
    if col_names:
        try:
            row_list = list(row)
            if len(col_names) == len(row_list):
                return dict(zip(col_names, row_list))
        except Exception:
            pass
    
    # For pyodbc.Row objects: they have keys() method and support __getitem__
    try:
        if hasattr(row, 'keys'):
            # Get column names from pyodbc Row
            col_names_from_row = list(row.keys())
            # Build dict from row values indexed by column names
            result = {}
            for i, col_name in enumerate(col_names_from_row):
                try:
                    val = row[col_name]
                    result[col_name] = val
                except Exception as col_err:
                    # Fallback to index-based access if column name doesn't work
                    try:
                        val = row[i]
                        result[col_name] = val
                    except Exception:
                        result[col_name] = None
            return result if result else row
    except Exception:
        pass
    
    # Fallback: return the raw row (supports index access like row[0], row[1])
    return row