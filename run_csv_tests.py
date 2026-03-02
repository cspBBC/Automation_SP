#!/usr/bin/env python
"""
Standalone script to execute keyword-driven CSV tests.
Users can update keyword_driven_tests.csv and run this script to execute all tests.
Each test case gets its own log file that updates on re-execution.
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_engine_layer.runner import run_stored_procedures_from_csv
from test_engine_layer.utils import setup_logging
from database_layer.connection import get_connection
from database_layer.transaction_manager import set_test_transaction, clear_test_transaction

def create_test_case_directory(test_case_id):
    """Create output directory for a specific test case."""
    output_dir = os.path.join('output', test_case_id)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def setup_file_logging_for_test(output_dir, test_case_id):
    """Configure file logging for a specific test case."""
    log_file = os.path.join(output_dir, 'execution.log')
    
    # Get root logger and set level
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Ensure root logger captures all levels
    
    # Remove previous file handlers for this logger
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.flush()  # Flush before closing
            handler.close()
            logger.removeHandler(handler)
    
    # Create file handler (overwrites on re-execution)
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    return log_file, file_handler  # Return handler so we can flush later

def save_test_case_details(output_dir, test_case_id, test_result):
    """Save detailed execution results for a test case."""
    details_file = os.path.join(output_dir, 'execution_details.json')
    
    team_id = None
    status = test_result.get('status', 'unknown')
    
    if status == 'passed':
        result_data = test_result.get('result', {})
        if isinstance(result_data, dict):
            chain_data = result_data.get('chain_data', {})
            team_id = chain_data.get('created_team_id')
    
    details = {
        'test_case_id': test_case_id,
        'timestamp': datetime.now().isoformat(),
        'status': status,
        'team_id': team_id,
        'error': test_result.get('error') if status == 'failed' else None,
        'full_result': test_result
    }
    
    # Overwrite on re-execution
    with open(details_file, 'w', encoding='utf-8') as f:
        json.dump(details, f, indent=2, default=str)
    
    return details_file, team_id

def main():
    """Execute all keyword-driven CSV tests within a transaction that rolls back."""
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*90)
    print("Keyword-Driven CSV Test Execution (with Savepoint-Based Rollback)")
    print("="*90)
    print("Creating individual test case folders in output/")
    print("Reading from: data_layer/test_data/keyword_driven_tests.csv")
    print("Auto-discovering module folders and templates...")
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
        
        if 'results' in results:
            for module_name, test_results in results['results'].items():
                for test_result in test_results:
                    test_case_id = test_result.get('case_id', 'unknown')
                    status = test_result.get('status', 'unknown')
                    
                    # Create directory for this test case
                    output_dir = create_test_case_directory(test_case_id)
                    
                    # Setup logging for this test case
                    log_file, file_handler = setup_file_logging_for_test(output_dir, test_case_id)
                    
                    # Get logger and log test details
                    test_logger = logging.getLogger('test_case')
                    test_logger.info(f"\n{'='*80}")
                    test_logger.info(f"Test Case: {test_case_id}")
                    test_logger.info(f"Module: {module_name}")
                    test_logger.info(f"Status: {status}")
                    test_logger.info(f"Execution Time: {datetime.now().isoformat()}")
                    test_logger.info(f"{'='*80}\n")
                    
                    if status == 'passed':
                        result_data = test_result.get('result', {})
                        if isinstance(result_data, dict):
                            chain_data = result_data.get('chain_data', {})
                            team_id = chain_data.get('created_team_id')
                            test_logger.info(f"✅ PASSED")
                            test_logger.info(f"Created Team ID: {team_id}")
                            test_case_summary.append({
                                'case_id': test_case_id,
                                'status': 'PASSED',
                                'team_id': team_id,
                                'output_dir': output_dir
                            })
                    elif status == 'failed':
                        error = test_result.get('error', 'Unknown error')
                        test_logger.error(f"❌ FAILED")
                        test_logger.error(f"Error: {error}")
                        test_case_summary.append({
                            'case_id': test_case_id,
                            'status': 'FAILED',
                            'error': error,
                            'output_dir': output_dir
                        })
                    else:
                        test_logger.warning(f"⏭️  SKIPPED")
                        test_case_summary.append({
                            'case_id': test_case_id,
                            'status': 'SKIPPED',
                            'output_dir': output_dir
                        })
                    
                    # Save details
                    details_file, team_id = save_test_case_details(output_dir, test_case_id, test_result)
                    test_logger.info(f"\nLogs saved to: {log_file}")
                    test_logger.info(f"Details saved to: {details_file}\n")
                    
                    # Flush the file handler to ensure logs are written to disk
                    file_handler.flush()
                    
                    # Print to console
                    print(f"Test Case: {test_case_id}")
                    print(f"Status: {status}")
                    if status == 'passed' and team_id:
                        print(f"Team ID: {team_id}")
                    elif status == 'failed':
                        print(f"Error: {test_result.get('error', 'Unknown')}")
                    print(f"Output: {output_dir}")
                    print()
        
        # Display overall summary
        print("\n" + "="*90)
        print("Overall Execution Summary")
        print("="*90)
        print(f"Total Tests:  {results['total_tests']}")
        print(f"Passed:       {results['passed']}")
        print(f"Failed:       {results['failed']}")
        print(f"Skipped:      {results['skipped']}")
        print("="*90)
        print("** All changes rolled back - database state unchanged **\n")
        
        print("Individual Test Logs:")
        for summary in test_case_summary:
            status_symbol = "✅" if summary['status'] == 'PASSED' else "❌" if summary['status'] == 'FAILED' else "⏭️"
            print(f"  {status_symbol} {summary['case_id']}: {summary['output_dir']}")
        print()
        
        # Return exit code based on failures
        if results['failed'] > 0:
            print(f"❌ {results['failed']} test(s) failed")
            return 1
        else:
            print(f"✅ All {results['passed']} test(s) passed!")
            return 0
            
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"\n❌ Execution failed: {e}")
        logger.exception("Traceback:")
        print(f"\n❌ Execution failed: {e}")
        
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
        # Flush all loggers to ensure logs are written to disk
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
        
        # Always rollback transaction and cleanup, regardless of success or failure
        if conn:
            try:
                # Final rollback of the outer transaction (savepoint already rolled back in try block)
                cursor = conn.cursor()
                cursor.execute("ROLLBACK TRANSACTION")
                cursor.close()
                logger.info("Outer transaction rolled back - all test data changes discarded")
                print("✅ Outer transaction rolled back - no data was persisted")
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
