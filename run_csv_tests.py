#!/usr/bin/env python
"""
Standalone script to execute keyword-driven CSV tests.
Users can update keyword_driven_tests.csv and run this script to execute all tests.
Comprehensive logs captured in pytest execution.log when run via pytest.
"""

import sys
import os
import io
import logging
from datetime import datetime

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_engine_layer.runner import run_stored_procedures_from_csv
from test_engine_layer.utils import setup_logging, get_test_type_for_test_case
from database_layer.connection import get_connection
from database_layer.transaction_manager import set_test_transaction, clear_test_transaction

def setup_execution_logging():
    """Setup file logging to execution.log in output folder."""
    output_dir = os.path.join('output', 'csv_execution')
    os.makedirs(output_dir, exist_ok=True)
    
    log_file = os.path.join(output_dir, 'execution.log')
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(file_handler)
    
    return log_file, file_handler


def is_expected_scenario_error(test_case_id: str, error_message: str) -> bool:
    """Check if a test case error is expected for scenario tests.
    
    Scenario tests that show FAILED status with expected error messages
    should be reported as PASSED (because the error is what we expect).
    
    Args:
        test_case_id: The test case ID (e.g., 'Create_Duplicate_Team_01')
        error_message: The error message from the test result
        
    Returns:
        True if the error is expected for this scenario test type
    """
    # Check if this is a scenario test
    try:
        test_type = get_test_type_for_test_case(test_case_id)
    except:
        return False  # Not found in CSV
    
    if test_type.lower() != 'scenario':
        return False  # Not a scenario test
    
    # Map scenario test case patterns to expected error messages
    expected_errors = {
        'Duplicate': 'already exists',
        'Invalid': 'invalid',
        'Missing': 'not found',
        'Access': 'access denied',
    }
    
    # Check if test case ID contains any scenario pattern
    for pattern, expected_error in expected_errors.items():
        if pattern.lower() in test_case_id.lower():
            # Check if the actual error message contains expected text
            if expected_error.lower() in error_message.lower():
                return True
    
    return False

def main():
    """Execute all keyword-driven CSV tests within a transaction that rolls back."""
    log_file, file_handler = setup_execution_logging()
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*90)
    print("Keyword-Driven CSV Test Execution (with Savepoint-Based Rollback)")
    print("="*90)
    print("Reading from: data_layer/test_data/keyword_driven_tests.csv")
    print("Auto-discovering module folders and templates...")
    print("Logging: Comprehensive logs saved to execution.log")
    print("** All changes (including SP internal COMMITs) will be ROLLED BACK **\n")
    
    # Create a connection and start a transaction context
    # This ensures all test data changes are rolled back after execution
    conn = None
    savepoint_name = "csv_test_savepoint"
    try:
        conn = get_connection()
        conn.autocommit = False  # Ensure autocommit is disabled
        set_test_transaction(conn)
        logger.info("Transaction context initialized - all changes will be rolled back")
        
        # Start a transaction
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        logger.info("Transaction started")
        
        # Create a savepoint - this allows us to rollback even if SP has internal COMMITs
        cursor.execute(f"SAVE TRANSACTION {savepoint_name}")
        logger.info(f"Savepoint '{savepoint_name}' created - handle SPs with internal COMMITs")
        cursor.close()
        
        # Execute all CSV tests with auto-discovery scaffold framework
        results = run_stored_procedures_from_csv()
        
        # Rollback to savepoint to undo all changes (including SP internal commits)
        cursor = conn.cursor()
        cursor.execute(f"ROLLBACK TRANSACTION {savepoint_name}")
        logger.info(f"Rolled back to savepoint '{savepoint_name}' - all changes discarded")
        cursor.close()
        
        # Process each test result and save individual logs
        print("\n" + "="*90)
        print("Test Case Results")
        print("="*90 + "\n")
        
        test_case_summary = []
        passed_count = 0
        failed_count = 0
        
        if 'results' in results:
            for module_name, test_results in results['results'].items():
                for test_result in test_results:
                    test_case_id = test_result.get('case_id', 'unknown')
                    status = test_result.get('status', 'unknown')
                    status_norm = str(status).lower()
                    error_msg = test_result.get('error', 'Unknown error')
                    
                    # Print to console only (detailed logging handled by pytest)
                    print(f"Test Case: {test_case_id}")
                    print(f"Status: {status}")
                    
                    # Check if FAILED status is actually an expected scenario error
                    if status_norm == 'failed' and is_expected_scenario_error(test_case_id, error_msg):
                        # Expected error for scenario test - treat as PASSED
                        print(f"[PASS] Scenario correctly rejected with error: {error_msg}\n")
                        test_case_summary.append({
                            'case_id': test_case_id,
                            'status': 'PASSED',
                            'error': error_msg,
                            'scenario_type': 'expected'
                        })
                        passed_count += 1
                    elif status_norm == 'passed':
                        result_data = test_result.get('result', {})
                        if isinstance(result_data, dict):
                            chain_data = result_data.get('chain_data', {})
                            team_id = chain_data.get('created_team_id')
                            print(f"[PASS] Team ID: {team_id}\n")
                            test_case_summary.append({
                                'case_id': test_case_id,
                                'status': 'PASSED',
                                'team_id': team_id
                            })
                            passed_count += 1
                    elif status_norm == 'failed':
                        print(f"[FAIL] Error: {error_msg}\n")
                        test_case_summary.append({
                            'case_id': test_case_id,
                            'status': 'FAILED',
                            'error': error_msg
                        })
                        failed_count += 1
                    else:
                        print(f"[SKIP] SKIPPED\n")
                        test_case_summary.append({
                            'case_id': test_case_id,
                            'status': 'SKIPPED'
                        })
        
        # Display overall summary
        print("="*90)
        print("Overall Execution Summary")
        print("="*90)
        print(f"Total Tests:  {results['total_tests']}")
        print(f"Passed:       {passed_count}")
        print(f"Failed:       {failed_count}")
        print(f"Skipped:      {results['skipped']}")
        print("="*90)
        print("** All changes rolled back - database state unchanged **")
        print(f"** Comprehensive logs: {os.path.abspath(log_file)} **\n")
        
        # Return exit code based on failures
        if failed_count > 0:
            print(f"[FAIL] {failed_count} test(s) failed")
            return 1
        else:
            print(f"[PASS] All {passed_count} test(s) passed!")
            return 0
            
    except Exception as e:
        if 'logger' in locals():
            logger.error(f"\n[FAIL] Execution failed: {e}")
            logger.exception("Traceback:")
        print(f"\n[FAIL] Execution failed: {e}")
        
        # Attempt to rollback on error
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(f"ROLLBACK TRANSACTION {savepoint_name}")
                cursor.close()
                logger.info("Rolled back to savepoint on error")
            except Exception as rollback_err:
                logger.error(f"Could not rollback to savepoint: {rollback_err}")
        
        return 1
    
    finally:
        # Flush and close file handler
        if file_handler:
            file_handler.flush()
            file_handler.close()
        
        # Always rollback transaction and cleanup, regardless of success or failure
        if conn:
            try:
                # Final rollback of the outer transaction (savepoint already rolled back in try block)
                cursor = conn.cursor()
                cursor.execute("ROLLBACK TRANSACTION")
                cursor.close()
                logger.info("Outer transaction rolled back - all test data changes discarded")
                print("[PASS] Outer transaction rolled back - no data was persisted")
            except Exception as e:
                logger.error(f"Error during rollback: {e}")
            
            # Clear the test transaction context
            clear_test_transaction()
            
            try:
                conn.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
