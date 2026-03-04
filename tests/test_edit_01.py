import pytest
from config.config import DataConfig
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import (
    get_test_case_ids_by_operation, 
    verify_preseed_for_module, 
    get_module_for_test_case
)
from data_loader_factory import TestDataLoader
from validation_layer.schGroup_validator import (
    getSchdGrpDetails,
    validateSchdGrpHistoryExists
)

TEST_USER_ID = 10201


def validate_workflow_dependencies():
    """Validate Create tests are enabled if Edit tests are enabled."""
    create_tests = get_test_case_ids_by_operation('Create')
    edit_tests = get_test_case_ids_by_operation('Edit')
    if edit_tests and not create_tests:
        pytest.skip("Edit tests enabled but no Create tests found")


# Get test case IDs
EDIT_TEST_CASES = get_test_case_ids_by_operation('Edit')


@pytest.fixture
def team_after_edit(db_transaction, request):
    """Execute Create->Edit workflow in isolated transaction, return team ID."""
    validate_workflow_dependencies()
    
    # Get first Create test case to verify preseed data
    create_cases = get_test_case_ids_by_operation('Create')
    if create_cases:
        verify_preseed_for_module(get_module_for_test_case(create_cases[0]))
    
    # Execute all operations (Create + Edit)
    result = run_stored_procedures_from_data()
    all_test_results = [r for module in result.get('results', {}).values() for r in module]
    
    # Find last successful Create result
    create_results = [r for r in all_test_results 
                      if r.get('Operation') == 'Create' and r.get('status') == 'PASSED'
                      and 'negative' not in r.get('Test Type', '').lower()]
    
    assert create_results, "No successful Create operation found"
    team_id = create_results[-1].get('execution_context', {}).get('created_team_id')
    assert team_id, "Create operation must return a team ID"
    
    # Validate Edit also passed
    edit_result = next((r for r in all_test_results if r.get('Operation') == 'Edit'), None)
    assert edit_result and edit_result.get('status') == 'PASSED', "Edit operation must pass"
    
    return {'team_id': team_id}


@pytest.mark.parametrize("team_after_edit", EDIT_TEST_CASES, indirect=True, ids=EDIT_TEST_CASES)
def test_edit_updates_team_successfully(team_after_edit):
    """Validate Edit workflow successfully creates and updates team."""
    team_id = team_after_edit['team_id']
    details = getSchdGrpDetails(team_id)
    assert details, f"Team {team_id} should exist"
    assert details.get('schedulingTeamId') == team_id
    assert validateSchdGrpHistoryExists(team_id, TEST_USER_ID)

    