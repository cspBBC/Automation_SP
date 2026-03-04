import pytest
import json
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import get_test_case_ids_by_operation, verify_preseed_for_module, get_module_for_test_case
from data_loader_factory import DataLoaderFactory
from validation_layer.schGroup_validator import (
    getSchdGrpDetails,
    getSchdGrpHistory,
    validateSchdGrpHistoryExists
)

TEST_USER_ID = 10201


def validate_dependencies(dependent_op: str, prerequisite_op: str):
    """Validate prerequisite operation is enabled if dependent is enabled."""
    dependent = get_test_case_ids_by_operation(dependent_op)
    prerequisite = get_test_case_ids_by_operation(prerequisite_op)
    if dependent and not prerequisite:
        pytest.skip(f"{dependent_op} enabled but no {prerequisite_op} tests found")


# Get test case IDs for parametrization
EDIT_TEST_CASES = get_test_case_ids_by_operation('Edit')


@pytest.fixture
def create_then_edit_result(db_transaction, request):
    """Execute Create, then Edit; extract expected team name from CSV."""
    validate_dependencies('Edit', 'Create')
    
    create_cases = get_test_case_ids_by_operation('Create')
    if create_cases:
        verify_preseed_for_module(get_module_for_test_case(create_cases[0]))
    
    result = run_stored_procedures_from_data()
    all_results = result.get('results', {})
    all_test_results = [r for module in all_results.values() for r in module]
    
    expected_team_name = None
    if hasattr(request, 'param'):
        csv_data = DataLoaderFactory.load('keyword_driven_tests.csv', loader_type='keyword_driven')
        for cases in csv_data.values():
            for case in cases:
                if case.get('case_id') == request.param:
                    expected_team_name = case.get('parameters', {}).get('schedulingTeamName')
    
    creates = [r for r in all_test_results 
               if r.get('Operation') == 'Create' and r.get('status') == 'PASSED'
               and 'negative' not in r.get('Test Type', '').lower()]
    created_team_id = creates[-1].get('execution_context', {}).get('created_team_id') if creates else None
    
    create_status = creates[-1].get('status') if creates else None
    edit_status = next((r.get('status') for r in all_test_results 
                       if r.get('Operation') == 'Edit'), None)
    
    assert created_team_id, "Create operation must return a team ID"
    assert create_status == 'PASSED', f"Create failed: {create_status}"
    assert edit_status == 'PASSED', f"Edit failed: {edit_status}"
    
    return {'team_id': created_team_id, 'expected_team_name': expected_team_name}


# Parametrize fixture with all Edit test cases
@pytest.mark.parametrize("create_then_edit_result", EDIT_TEST_CASES, indirect=True, ids=EDIT_TEST_CASES)
def test_edit_updates_team_successfully(create_then_edit_result):
    team_id = create_then_edit_result['team_id']
    expected = create_then_edit_result.get('expected_team_name')
    details = getSchdGrpDetails(team_id)
    assert details, f"Team {team_id} should exist"
    assert details.get('schedulingTeamId') == team_id
    if expected:
        assert details.get('schedulingTeamName') == expected
    assert validateSchdGrpHistoryExists(team_id, TEST_USER_ID)

    