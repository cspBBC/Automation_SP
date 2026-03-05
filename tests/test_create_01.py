"""Test Create operations using pytest framework."""

import pytest
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import get_test_case_ids_by_operation
from validation_layer.schGroup_validator import getSchdGrpDetails


CREATE_TEST_CASES = [tc for tc in get_test_case_ids_by_operation('Create') if 'Duplicate' not in tc]
DUPLICATE_TEST_CASES = [tc for tc in get_test_case_ids_by_operation('Create') if 'Duplicate' in tc]


@pytest.mark.parametrize("test_case_id", CREATE_TEST_CASES, ids=CREATE_TEST_CASES)
def test_create_team(db_transaction, logger, test_case_id):
    """Execute non-duplicate Create test cases."""
    result = run_stored_procedures_from_data(filter_test_name=test_case_id)
    
    module_results = list(result.get('results', {}).values())[0]
    test_result = [r for r in module_results if r.get('case_id') == test_case_id][0]
    
    status = test_result.get('status', '').upper()
    team_id = test_result.get('execution_context', {}).get('created_team_id')
    
    assert status in ['SUCCESS', 'PASSED'], f"Expected success but got {status}"
    assert team_id, f"Create should return team_id"
    
    team_details = getSchdGrpDetails(team_id)
    assert team_details.get('schedulingTeamId') == team_id
    
    logger.info(f"✓ Team {team_id} created successfully")


@pytest.mark.parametrize("test_case_id", DUPLICATE_TEST_CASES, ids=DUPLICATE_TEST_CASES)
def test_create_duplicate_prevention(db_transaction, logger, test_case_id):
    """Test duplicate prevention - duplicate must fail when same team exists.
    
    Runs all Create tests in same transaction so baseline team exists when 
    duplicate test executes.
    """
    # Run ALL Create tests in same transaction for duplicate detection
    result = run_stored_procedures_from_data()
    
    module_results = list(result.get('results', {}).values())[0]
    test_result = [r for r in module_results if r.get('case_id') == test_case_id][0]
    
    status = test_result.get('status', '').upper()
    
    # Duplicate test MUST FAIL
    assert status == 'FAILED', f"Duplicate prevention failed - test passed when it should fail"
    
    logger.info(f"✓ Duplicate prevention validated - duplicate correctly rejected")
