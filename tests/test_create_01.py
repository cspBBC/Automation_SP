"""Test Create operations - simple keyword-driven approach."""

import pytest
import json
from pathlib import Path
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import (
    get_test_case_ids_by_operation,
    get_module_for_test_case,
    validate_csv_configuration,
    setup_logging
)
from database_layer.connection import DBSession
from validation_layer.schGroup_validator import getSchdGrpDetails


# Validate CSV configuration at module load time
validate_csv_configuration()

logger = setup_logging()

# Get enabled test cases (exclude Duplicate tests - they need to run with Create in same transaction)
CREATE_TEST_CASES = [tc for tc in get_test_case_ids_by_operation('Create') if 'Duplicate' not in tc]


@pytest.fixture
def db_team_id(db_transaction):
    """Fixture to store and pass team_id between Create and Edit tests."""
    return {'team_id': None}


@pytest.mark.parametrize("test_case_id", CREATE_TEST_CASES, ids=CREATE_TEST_CASES)
def test_create_team(db_transaction, db_team_id, test_case_id):
    """Execute Create test case and capture team_id for Edit tests.
    
    - Runs stored procedure with test parameters

    - For first successful Create, captures team_id
    - Stores team_id in fixture for Edit workflow
    """
    module = get_module_for_test_case(test_case_id)
    
    logger.info(f"\nExecuting: {test_case_id}")
    
    # Run the test case
    result = run_stored_procedures_from_data(filter_test_name=test_case_id)
    
    # Extract results
    module_results = list(result.get('results', {}).values())[0]
    test_result = next((r for r in module_results if r.get('case_id') == test_case_id), None)
    
    if not test_result:
        raise AssertionError(f"No result found for test case '{test_case_id}'")
    
    status = test_result.get('status', '').upper()
    created_team_id = test_result.get('execution_context', {}).get('created_team_id')
    message = test_result.get('message', '') or test_result.get('error', '')
    
    logger.info(f"Status: {status}")
    if created_team_id:
        logger.info(f"Created Team ID: {created_team_id}")
    if message:
        logger.info(f"Message: {message}")
    
    # Success - store team_id for Edit tests
    assert status == 'SUCCESS' or status == 'PASSED', f"Expected success but got {status}: {message}"
    assert created_team_id, f"Create should return team_id but got: {created_team_id}"
    
    # Store team_id for Edit tests
    if db_team_id['team_id'] is None:
        db_team_id['team_id'] = created_team_id
        logger.info(f"✓ Team ID captured for Edit workflow: {created_team_id}")
    
    # Validate team was actually created in DB
    team_details = getSchdGrpDetails(created_team_id)
    assert team_details.get('schedulingTeamId') == created_team_id, f"Team {created_team_id} not found in DB"
    logger.info(f"✓ Team {created_team_id} validated in database")


def test_duplicate_team_same_transaction(db_transaction, db_team_id):
    """Test duplicate prevention - works with ANY enabled Create test.
    
    This test verifies:
    1. Any enabled Create test runs and succeeds
    2. Duplicate Create test runs and fails with duplicate error
    
    Independent of which specific Create test is enabled - works with ANY.
    """
    # Check if Duplicate test is enabled in CSV
    enabled_duplicates = [tc for tc in get_test_case_ids_by_operation('Create') if 'Duplicate' in tc]
    if not enabled_duplicates:
        pytest.skip("Duplicate test is not enabled in CSV (Executed=no). To test duplicate prevention, set Create_Duplicate_Team_01 Executed=yes")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing Duplicate Prevention (works with ANY Create test)")
    logger.info(f"{'='*80}")
    
    # Run ALL tests (Create + Duplicate) in one transaction
    result = run_stored_procedures_from_data()
    
    # Extract all Create results
    all_results = []
    for module_results in result.get('results', {}).values():
        all_results.extend([r for r in module_results if 'Create' in r.get('case_id', '')])
    
    # Find the first successful Create test (could be any Create test)
    successful_creates = [r for r in all_results if r.get('status', '').upper() in ['SUCCESS', 'PASSED'] and 'Duplicate' not in r.get('case_id', '')]
    
    if not successful_creates:
        pytest.fail("DUPLICATE TEST REQUIRES: At least ONE regular Create test (non-Duplicate) must be enabled (Executed=yes in CSV).\n"
                   "To test duplicate prevention, enable Create_New_Schd_Team_01 or another Create test.")
    
    create_baseline = successful_creates[0]
    baseline_case_id = create_baseline.get('case_id', 'Unknown')
    baseline_status = create_baseline.get('status', '').upper()
    baseline_team_id = create_baseline.get('execution_context', {}).get('created_team_id')
    baseline_msg = create_baseline.get('message', '') or create_baseline.get('error', '')
    
    logger.info(f"\n[Step 1] ANY Successful Create Test: {baseline_case_id}")
    logger.info(f"  Status: {baseline_status}")
    logger.info(f"  Team ID: {baseline_team_id}")
    logger.info(f"  Message: {baseline_msg if baseline_msg else '(success - no message)'}")
    
    assert baseline_team_id, f"Create should have team_id"
    
    # Find Duplicate test result (should fail)
    create_duplicate = next((r for r in all_results if 'Duplicate' in r.get('case_id', '')), None)
    
    if not create_duplicate:
        logger.warning("No Duplicate test found - skipping duplicate validation")
        return
    
    dup_status = create_duplicate.get('status', '').upper()
    dup_team_id = create_duplicate.get('execution_context', {}).get('created_team_id')
    dup_msg = create_duplicate.get('message', '') or create_duplicate.get('error', '')
    
    logger.info(f"\n[Step 2] Duplicate Attempt (same name, same division):")
    logger.info(f"  Status: {dup_status}")
    logger.info(f"  Team ID: {dup_team_id}")
    logger.info(f"  Error Message: {dup_msg}")
    
    # Should FAIL with duplicate error
    assert dup_status not in ['SUCCESS', 'PASSED'], f"Duplicate should fail, but got {dup_status}"
    assert 'duplicate' in dup_msg.lower() or 'already exists' in dup_msg.lower(), \
        f"Expected duplicate error, got: {dup_msg}"
    
    logger.info(f"\n✓ DUPLICATE PREVENTION WORKING!")
    logger.info(f"✓ Works with ANY Create test ({baseline_case_id})")
    logger.info(f"✓ System Error: {dup_msg}")
    logger.info(f"{'='*80}\n")
