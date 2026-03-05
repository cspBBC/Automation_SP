"""Test Create operations using pytest framework."""

import pytest
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import get_test_case_ids_by_operation
from validation_layer.schGroup_validator import getSchdGrpDetails


CREATE_TEST_CASES = get_test_case_ids_by_operation('Create')


@pytest.mark.parametrize("test_case_id", CREATE_TEST_CASES, ids=CREATE_TEST_CASES)
def test_create_team(db_transaction, logger, test_case_id):
    """Execute enabled Create test cases via runner."""
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
