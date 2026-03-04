import pytest
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import (
    get_test_case_ids_by_operation, 
    verify_preseed_for_module, 
    get_module_for_test_case,
    get_test_type_for_test_case
)
from validation_layer.schGroup_validator import getSchdGrpDetails


def validate_scenario_dependencies():
    """Validate at least one independent Create test is enabled for scenario tests."""
    ind = get_test_case_ids_by_operation('Create', test_type='independent')
    scn = (get_test_case_ids_by_operation('Create', test_type='scenario') + 
           get_test_case_ids_by_operation('Create', test_type='negative-scenario'))
    if scn and not ind:
        pytest.skip("Scenario tests enabled but no independent Create found")


# Get test case IDs
CREATE_TEST_CASES = get_test_case_ids_by_operation('Create', test_type='independent')
SCENARIO_TEST_CASES = (get_test_case_ids_by_operation('Create', test_type='scenario') + 
                       get_test_case_ids_by_operation('Create', test_type='negative-scenario'))


@pytest.fixture
def created_team_id(db_transaction, request):
    """Execute independent test case in isolated transaction."""
    test_case = request.param
    verify_preseed_for_module(get_module_for_test_case(test_case))
    result = run_stored_procedures_from_data(filter_test_name=test_case)
    team_id = list(result.get('results', {}).values())[0][0].get('execution_context', {}).get('created_team_id')
    return {'team_id': team_id}

@pytest.mark.parametrize("created_team_id", CREATE_TEST_CASES, indirect=True, ids=CREATE_TEST_CASES)
def test_validate_created_team(created_team_id):
    """Validate independent Create test case."""
    team_id = created_team_id.get('team_id')
    assert getSchdGrpDetails(team_id).get('schedulingTeamId') == team_id


@pytest.fixture
def scenario_test_result(db_transaction, request):
    """Execute all tests in shared transaction, return specified scenario result."""
    validate_scenario_dependencies()
    if not SCENARIO_TEST_CASES:
        pytest.skip("No scenario tests defined")
    verify_preseed_for_module(get_module_for_test_case(SCENARIO_TEST_CASES[0]))
    result = run_stored_procedures_from_data()
    module_results = list(result.get('results', {}).values())[0]
    return next((r for r in module_results if r.get('case_id') == request.param), None)


@pytest.mark.parametrize("scenario_test_result", SCENARIO_TEST_CASES, indirect=True, ids=SCENARIO_TEST_CASES)
def test_scenario_constraint_validation(scenario_test_result):
    """Validate scenario test identifies constraint violations."""
    case_id = scenario_test_result.get('case_id')
    status = scenario_test_result.get('status')
    test_type = get_test_type_for_test_case(case_id)
    message = scenario_test_result.get('message') or scenario_test_result.get('error', '')
    
    if 'negative' in test_type.lower():
        assert status == 'FAILED'
        assert any(x in message.lower() for x in ['already exists', 'duplicate', 'unique'])



