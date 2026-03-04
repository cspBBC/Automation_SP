"""Test Create operations - simple keyword-driven approach."""

import pytest
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import (
    get_test_case_ids_by_operation,
    get_module_for_test_case,
)
from validation_layer.schGroup_validator import getSchdGrpDetails


CREATE_TEST_CASES = [tc for tc in get_test_case_ids_by_operation('Create') if 'Duplicate' not in tc]


@pytest.mark.parametrize("test_case_id", CREATE_TEST_CASES, ids=CREATE_TEST_CASES)
def test_create_team(db_transaction, logger, test_case_id):
    """Execute Create test case."""
    module = get_module_for_test_case(test_case_id)
    logger.info(f"\nExecuting: {test_case_id}")
    
    result = run_stored_procedures_from_data(filter_test_name=test_case_id)
    
    module_results = list(result.get('results', {}).values())[0]
    test_result = next((r for r in module_results if r.get('case_id') == test_case_id), None)
    
    assert test_result, f"No result found for test case '{test_case_id}'"
    
    status = test_result.get('status', '').upper()
    created_team_id = test_result.get('execution_context', {}).get('created_team_id')
    message = test_result.get('message', '') or test_result.get('error', '')
    
    assert status in ['SUCCESS', 'PASSED'], f"Expected success but got {status}: {message}"
    assert created_team_id, f"Create should return team_id but got: {created_team_id}"
    
    team_details = getSchdGrpDetails(created_team_id)
    assert team_details.get('schedulingTeamId') == created_team_id, f"Team {created_team_id} not found in DB"
    
    logger.info(f"✓ Team {created_team_id} created successfully")


def test_duplicate_team_same_transaction(db_transaction, logger):
    """Test duplicate prevention - works with ANY enabled Create test."""
    enabled_duplicates = [tc for tc in get_test_case_ids_by_operation('Create') if 'Duplicate' in tc]
    if not enabled_duplicates:
        pytest.skip("Duplicate test is not enabled in test data (Executed=no)")
    
    logger.info(f"\nTesting Duplicate Prevention")
    result = run_stored_procedures_from_data()
    
    all_results = []
    for module_results in result.get('results', {}).values():
        all_results.extend([r for r in module_results if 'Create' in r.get('case_id', '')])
    
    successful_creates = [r for r in all_results if r.get('status', '').upper() in ['SUCCESS', 'PASSED'] and 'Duplicate' not in r.get('case_id', '')]
    if not successful_creates:
        pytest.fail("DUPLICATE TEST REQUIRES: At least ONE regular Create test must be enabled in test data")
    
    baseline = successful_creates[0]
    baseline_case_id = baseline.get('case_id', 'Unknown')
    baseline_team_id = baseline.get('execution_context', {}).get('created_team_id')
    
    logger.info(f"Baseline Create: {baseline_case_id} (Team ID: {baseline_team_id})")
    assert baseline_team_id, "Create should have team_id"
    
    duplicate = next((r for r in all_results if 'Duplicate' in r.get('case_id', '')), None)
    if not duplicate:
        logger.warning("No Duplicate test found")
        return
    
    dup_status = duplicate.get('status', '').upper()
    dup_msg = duplicate.get('message', '') or duplicate.get('error', '')
    
    logger.info(f"Duplicate Attempt: {dup_status}")
    assert dup_status not in ['SUCCESS', 'PASSED'], f"Duplicate should fail but got {dup_status}"
    assert 'duplicate' in dup_msg.lower() or 'already exists' in dup_msg.lower(), f"Expected duplicate error: {dup_msg}"
    
    logger.info(f"✓ Duplicate Prevention Working!")
