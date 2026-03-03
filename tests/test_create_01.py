import pytest
from test_engine_layer.runner import run_stored_procedures_from_csv
from test_engine_layer.utils import get_test_case_ids_by_operation, verify_preseed_for_module, get_module_for_test_case
from validation_layer.schGroup_validator import getSchdGrpDetails

# Get test case IDs for parametrization
CREATE_TEST_CASES = get_test_case_ids_by_operation('Create')

@pytest.fixture
def created_team_id(db_transaction, request):
    """Fixture that executes a specific test case independently and returns its created team ID."""
    test_case_name = request.param
    
    # Verify preseed data exists for this module
    module_name = get_module_for_test_case(test_case_name)
    verify_preseed_for_module(module_name)
    
    # Execute ONLY the specified test case (filter_test_name ensures independence)
    result = run_stored_procedures_from_csv(filter_test_name=test_case_name)
    
    # Extract team ID from the test result
    all_results = result.get('results', {})
    assert all_results, f"No results for test case {test_case_name}"
    
    # Get the first (and should be only) module's results
    module_results = list(all_results.values())[0]
    assert module_results, f"No results for test case {test_case_name}"
    
    team_id = module_results[0].get('execution_context', {}).get('created_team_id')
    assert team_id, f"Test case {test_case_name} should return a valid team ID"
    
    return team_id


# Parametrize the fixture with all Create test cases
@pytest.mark.parametrize("created_team_id", CREATE_TEST_CASES, indirect=True, ids=CREATE_TEST_CASES)
def test_validate_created_team(created_team_id):
    """Validate each created team independently.
    
    This test:
    - Runs for EACH Create test case in CSV (Executed=Yes)
    - Each test case executes independently without affecting others
    - Can be extended to add more test cases simply by adding CSV rows
    
    Validations:
    - Team details are returned  
    - Team ID matches expected value
    - Team exists in the system
    """
    team_id = created_team_id
    
    # Retrieve team details from DB
    details = getSchdGrpDetails(team_id)
    assert details, "Team details should be returned"
    assert details.get('schedulingTeamId') == team_id, "Returned team ID should match created team ID"
    
    # Note: Different test cases may have different properties:
    # - Some teams are Active (isActive=1), others may be Inactive (isActive=0)
    # - Different users create different teams
    # - Each test case is independent
    print(f"\n✓ Team {team_id} created and validated successfully")
    print(f"  - Team Name: {details.get('schedulingTeamName')}")
    print(f"  - Active Status: {details.get('isActive')}")
    print(f"  - Division ID: {details.get('divisionid')}")

