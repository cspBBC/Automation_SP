"""Test Edit operations using pytest framework."""

import pytest
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import get_test_case_ids_by_operation
from validation_layer.schGroup_validator import (
    getSchdGrpDetails,
    validateSchdGrpHistoryExists
)


EDIT_TEST_CASES = get_test_case_ids_by_operation('Edit')


@pytest.mark.parametrize("test_case_id", EDIT_TEST_CASES, ids=EDIT_TEST_CASES)
def test_edit_with_any_create(db_transaction, logger, test_case_id):
    """Execute Edit with ANY enabled Create TC - pick first available."""
    # Run all tests (will include any enabled Create and this Edit)
    # Edit will use whichever Create TC is enabled
    result = run_stored_procedures_from_data()
    
    # Results are organized by module -> list of test results
    module_results = list(result.get('results', {}).values())[0]
    
    # Find the Edit test result
    edit_result = [r for r in module_results if r.get('case_id') == test_case_id][0]
    
    status = edit_result.get('status', '').upper()
    team_id = edit_result.get('execution_context', {}).get('created_team_id')
    
    assert status in ['SUCCESS', 'PASSED'], f"Expected success but got {status}"
    assert team_id, f"Edit should return team_id"
    
    team_details = getSchdGrpDetails(team_id)
    assert team_details.get('schedulingTeamId') == team_id
    
    history_exists = validateSchdGrpHistoryExists(team_id, user_id=10201)
    assert history_exists, f"History not recorded for team {team_id}"
    
    logger.info(f"✓ Team {team_id} updated and validated")