"""Test Edit operations - simple keyword-driven approach."""

import pytest
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import (
    get_test_case_ids_by_operation,
    get_module_for_test_case,
)
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
    
    Note: For Edit to work, a Create test must have been enabled to create the team first.
          The test data should ensure Create_New_Schd_Team_02 and Update_Schd_Team_02 are configured together.
    """
    module = get_module_for_test_case(test_case_id)
    
    logger.info(f"\nExecuting: {test_case_id}")
    logger.info(f"Expected: Success")
    
    # Run all tests (Create + Edit) in the workflow
    result = run_stored_procedures_from_data()
    
    # Extract all results
    all_results = []
    for module_results in result.get('results', {}).values():
        all_results.extend(module_results)
    
    # Find the Edit test result
    test_result = next((r for r in all_results if r.get('case_id') == test_case_id), None)
    
    if not test_result:
        raise AssertionError(f"No result found for test case '{test_case_id}'")
    
    status = test_result.get('status', '').upper()
    team_id = test_result.get('execution_context', {}).get('created_team_id')
    message = test_result.get('message', '') or test_result.get('error', '')
    
    logger.info(f"Status: {status}")
    if team_id:
        logger.info(f"Team ID: {team_id}")
    if message:
        logger.info(f"Message: {message}")
    
    # Validate that Edit was successful
    assert status == 'SUCCESS' or status == 'PASSED', f"Expected success but got {status}: {message}"
    assert team_id, f"Edit should return team_id but got: {team_id}"
    
    # Validate team was updated in DB
    team_details = getSchdGrpDetails(team_id)
    assert team_details.get('schedulingTeamId') == team_id, f"Team {team_id} not found in DB"
    
    # Validate history was recorded
    history_exists = validateSchdGrpHistoryExists(team_id, user_id=10201)
    assert history_exists, f"History not recorded for team {team_id}"
    
    logger.info(f"✓ Team {team_id} updated and validated in database")
    logger.info(f"✓ History record created for team {team_id}")
