import pytest
from test_engine_layer.runner import run_stored_procedures_from_csv
from test_engine_layer.utils import (
    get_test_case_ids_by_operation, 
    verify_preseed_for_module, 
    get_module_for_test_case,
    get_test_type_for_test_case
)
from validation_layer.schGroup_validator import getSchdGrpDetails

# Get independent Create test cases (run in isolated transactions)
CREATE_TEST_CASES = get_test_case_ids_by_operation('Create', test_type='independent')

# Get scenario Create test cases (run in shared transaction)
SCENARIO_TEST_CASES = get_test_case_ids_by_operation('Create', test_type='scenario')

@pytest.fixture
def created_team_id(db_transaction, request):
    """Fixture that executes independent test cases in isolated transactions.
    
    Each independent test case runs with filter_test_name in its own transaction.
    """
    test_case_name = request.param
    
    # Verify preseed data exists for this module
    module_name = get_module_for_test_case(test_case_name)
    verify_preseed_for_module(module_name)
    
    # Execute ONLY the specified test case (filter_test_name ensures independence)
    result = run_stored_procedures_from_csv(filter_test_name=test_case_name)
    
    # Extract results
    all_results = result.get('results', {})
    assert all_results, f"No results for test case {test_case_name}"
    
    module_results = list(all_results.values())[0]
    assert module_results, f"No results for test case {test_case_name}"
    
    test_result = module_results[0]
    execution_context = test_result.get('execution_context', {})
    
    # Return dict with team_id and metadata
    return {
        'team_id': execution_context.get('created_team_id'),
        'test_case_name': test_case_name,
    }


# Parametrize the fixture with independent Create test cases
@pytest.mark.parametrize("created_team_id", CREATE_TEST_CASES, indirect=True, ids=CREATE_TEST_CASES)
def test_validate_created_team(created_team_id):
    """Validate each independent created team.
    
    This test runs for each Create test case marked as Test Type='independent'.
    Each test case executes independently in its own transaction.
    """
    result = created_team_id
    team_id = result.get('team_id')
    test_case_name = result.get('test_case_name')
    
    # Retrieve team details from DB
    details = getSchdGrpDetails(team_id)
    assert details, "Team details should be returned from database"
    assert details.get('schedulingTeamId') == team_id, "Returned team ID should match created team ID"
    
    print(f"\n✓ Team {team_id} created and validated successfully")
    print(f"  - Team Name: {details.get('schedulingTeamName')}")
    print(f"  - Active Status: {details.get('isActive')}")
    print(f"  - Division ID: {details.get('divisionid')}")


@pytest.fixture
def scenario_results(db_transaction):
    """Fixture that runs scenario test cases in SAME transaction.
    
    This fixture:
    - Runs ALL test cases without filtering (both independent and scenario cases)
    - Scenario cases execute in the SAME database transaction as other scenario cases
    - Allows detection of constraint violations and error conditions
    
    Returns all results from the shared-transaction execution.
    """
    if not SCENARIO_TEST_CASES:
        pytest.skip("No scenario tests defined for Create operation")
    
    # Get module from first scenario case
    module_name = get_module_for_test_case(SCENARIO_TEST_CASES[0])
    verify_preseed_for_module(module_name)
    
    # Execute ALL test cases WITHOUT filter - all in same transaction
    result = run_stored_procedures_from_csv()
    
    return result.get('results', {})


def test_scenarios(scenario_results):
    """Validate all scenario test cases in shared transaction.
    
    This generic test validates constraint violations and error scenarios:
    - Duplicate entries
    - Invalid references
    - Access control violations
    - etc.
    
    Scenario tests run in shared transaction to properly detect database constraints.
    The validation logic is driven by test case definitions in the CSV.
    """
    if not SCENARIO_TEST_CASES:
        pytest.skip("No scenario tests defined")
    
    all_results = scenario_results
    
    # Extract Create operation results
    module_results = list(all_results.values())[0]
    create_results = [r for r in module_results if r.get('Operation') == 'Create']
    
    # Get independent results (should all pass)
    independent_results = [r for r in create_results 
                          if get_test_type_for_test_case(r.get('case_id', '')) == 'independent']
    
    # Get scenario results
    scenario_result_list = [r for r in create_results 
                           if get_test_type_for_test_case(r.get('case_id', '')) == 'scenario']
    
    # Validate independent cases passed
    assert independent_results, "Should have independent Create cases"
    for ind_result in independent_results:
        assert ind_result.get('status') == 'PASSED', \
            f"Independent case {ind_result.get('case_id')} should pass"
        print(f"✓ Independent: {ind_result.get('case_id')} PASSED")
    
    # Validate scenario cases show expected errors
    assert scenario_result_list, "Should have scenario Create cases"
    for scenario in scenario_result_list:
        case_id = scenario.get('case_id', '')
        status = scenario.get('status', '')
        message = scenario.get('message', '') or scenario.get('error', '')
        
        # Scenario tests should FAIL (that's the point)
        assert status == 'FAILED', f"Scenario case {case_id} should fail"
        
        # Validate error message matches scenario type
        # For now, check for duplicate error (can be extended for other scenarios)
        assert 'already exists' in message.lower(), \
            f"Expected 'already exists' error for {case_id}, got: {message}"
        
        print(f"✓ Scenario: {case_id} correctly rejected with error")
        print(f"  - Error: {message}")


