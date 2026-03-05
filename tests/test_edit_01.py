"""Test Edit operations - simple keyword-driven approach."""

import pytest
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import get_test_case_ids_by_operation
from validation_layer.schGroup_validator import (
    getSchdGrpDetails,
    validateSchdGrpHistoryExists
)


EDIT_TEST_CASES = get_test_case_ids_by_operation('Edit')


@pytest.mark.parametrize("test_case_id", EDIT_TEST_CASES, ids=EDIT_TEST_CASES)
def test_edit_team(db_transaction, logger, test_case_id):
    """Execute Edit test case.
    
    - Edit tests use team_id created by Create operation
    - Both operations run in same transaction
    - Validates team is updated correctly
    """
    result = run_stored_procedures_from_data()
    
    all_results = []
    for module_results in result.get('results', {}).values():
        all_results.extend(module_results)
    
    matches = [r for r in all_results if r.get('case_id') == test_case_id]
    test_result = matches[0] if matches else None
    
    assert test_result, f"No result found for test case '{test_case_id}'"
    
    status = test_result.get('status', '').upper()
    team_id = test_result.get('execution_context', {}).get('created_team_id')
    
    assert status in ['SUCCESS', 'PASSED'], f"Expected success but got {status}"
    assert team_id, f"Edit should return team_id"
    
    team_details = getSchdGrpDetails(team_id)
    assert team_details.get('schedulingTeamId') == team_id
    
    history_exists = validateSchdGrpHistoryExists(team_id, user_id=10201)
    assert history_exists, f"History not recorded for team {team_id}"
    
    logger.info(f"✓ Team {team_id} updated and validated")
