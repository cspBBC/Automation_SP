import pytest
from test_engine_layer.runner import run_stored_procedures_from_csv
from test_engine_layer.utils import get_test_case_ids_by_operation, verify_preseed_for_module, get_module_for_test_case
from validation_layer.schGroup_validator import (
    getSchdGrpDetails,
    getSchdGrpHistory,
    validateSchdGrpHistoryExists
)

TEST_USER_ID = 10201


# Get test case IDs for parametrization
EDIT_TEST_CASES = get_test_case_ids_by_operation('Edit')


@pytest.fixture
def create_then_edit_result(db_transaction, output_dir, request):
    """Fixture that executes Create first, then Edit independently.
    
    Args:
        db_transaction: Database transaction context for test isolation
        output_dir: Output directory for test logs and artifacts
        request: Pytest request object for parametrization
    """
    # Verify preseed for the module (both Create and Edit use same module)
    create_cases = get_test_case_ids_by_operation('Create')
    if create_cases:
        module_name = get_module_for_test_case(create_cases[0])
        verify_preseed_for_module(module_name)
    
    # Execute all CSV tests (Create + Edit in workflow sequence)
    result = run_stored_procedures_from_csv()
    
    # Extract results from all modules
    all_results = result.get('results', {})
    assert all_results, "No results from CSV execution"
    
    # Flatten results from all modules
    all_test_results = []
    for module_results in all_results.values():
        all_test_results.extend(module_results)
    
    # Extract Create and Edit operation results
    created_team_id = None
    create_status = None
    edit_status = None
    
    for test_result in all_test_results:
        operation = test_result.get('Operation', '')
        status = test_result.get('status')
        
        if operation == 'Create':
            create_status = status
            created_team_id = test_result.get('execution_context', {}).get('created_team_id')
        elif operation == 'Edit':
            edit_status = status
    
    # Validate both operations succeeded
    assert created_team_id, "Create operation must return a team ID"
    assert create_status == 'PASSED', f"Create failed: {create_status}"
    assert edit_status == 'PASSED', f"Edit failed: {edit_status}"
    
    return {'team_id': created_team_id}


# Parametrize fixture with all Edit test cases
@pytest.mark.parametrize("create_then_edit_result", EDIT_TEST_CASES, indirect=True, ids=EDIT_TEST_CASES)
def test_edit_updates_team_successfully(create_then_edit_result):
    """Validate Edit operation successfully updates team.
    
    This test:
    - Runs for EACH Edit test case in CSV (Executed=Yes)
    - Create executes first to set up baseline team
    - Edit operates on that created team
    - All within independent test context
    - Each Edit test case runs independently without dependencies
    
    Validations:
    - Team exists after edit
    - Team properties were updated
    - History was logged for edit operation
    """
    team_id = create_then_edit_result['team_id']
    
    # Verify team still exists with same ID
    details = getSchdGrpDetails(team_id)
    assert details, f"Team {team_id} should exist after edit"
    assert details.get('schedulingTeamId') == team_id, "Team ID should be unchanged"
    
    # Verify team name was updated to edited version
    current_name = details.get('schedulingTeamName', '')
    assert current_name == 'tst automation schd grwp11_edited', \
        f"Team name should be 'tst automation schd grwp11_edited', got '{current_name}'"
    
    # Verify history logged the operations
    history = getSchdGrpHistory(team_id, TEST_USER_ID)
    assert history, "History should be recorded for edit operation"
    assert validateSchdGrpHistoryExists(team_id, TEST_USER_ID), \
        "History should be logged for Edit operation"
    
    print(f"\n✅ Team {team_id} edited successfully")
    print(f"  - Original Name: tst automation schd grwp11")
    print(f"  - Updated Name: {current_name}")
    print(f"  - History Entries: {len(history)}")

    