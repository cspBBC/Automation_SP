"""Test Create operations - simple keyword-driven approach."""

import pytest
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import get_test_case_ids_by_operation
from validation_layer.schGroup_validator import getSchdGrpDetails


CREATE_TEST_CASES = [tc for tc in get_test_case_ids_by_operation('Create') if 'Duplicate' not in tc]


@pytest.mark.parametrize("test_case_id", CREATE_TEST_CASES, ids=CREATE_TEST_CASES)
def test_create_team(db_transaction, logger, test_case_id):
    """Execute Create test case."""
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
    """Test duplicate prevention."""
    # Skip if duplicate test not enabled
    if not [tc for tc in get_test_case_ids_by_operation('Create') if 'Duplicate' in tc]:
        pytest.skip("Duplicate test not enabled (Executed=no)")
    
    logger.info("\nTesting Duplicate Prevention")
    result = run_stored_procedures_from_data()
    
    all_results = []
    for module_results in result.get('results', {}).values():
        all_results.extend([r for r in module_results if 'Create' in r.get('case_id', '')])
    
    # Verify baseline Create succeeded
    baseline = next((r for r in all_results if 'Duplicate' not in r.get('case_id', '')), None)
    assert baseline and baseline.get('status', '').upper() in ['SUCCESS', 'PASSED']
    
    # Verify Duplicate was rejected
    duplicate = next((r for r in all_results if 'Duplicate' in r.get('case_id', '')), None)
    assert duplicate and duplicate.get('status', '').upper() not in ['SUCCESS', 'PASSED']
    
    logger.info("✓ Duplicate Prevention Working!")
