import pytest
import json
from test_engine_layer.runner import run_stored_procedures_from_csv
from validation_layer.preseed_validator import verify_preseed_exists
from validation_layer.schGroup_validator import (
    getSchdGrpDetails,
    getSchdGrpHistory,
    validateSchdGrpHistoryExists
)

TEST_USER_ID = 10201
NEWS_DIVISION_ID = 6


@pytest.fixture
def create_then_edit_result(db_transaction, request):
    """
    Execute Create + Edit from CSV in single transaction.
    Returns: {team_id, create_status, edit_status}
    """
    verify_preseed_exists(request.fspath, 'createSchdGroup_user.sql')
    verify_preseed_exists(request.fspath, 'createSchdGroup_division.sql')

    # Execute all stored procedures from CSV (Create + Edit)
    execute_result = run_stored_procedures_from_csv()
    
    all_results = execute_result.get('results', {})
    created_team_id = None
    create_status = None
    edit_status = None
    
    # Extract results
    for module_name, test_results in all_results.items():
        for test_result in test_results:
            operation = test_result.get('Operation', '')
            status = test_result.get('status', '')
            
            if operation == 'Create':
                create_status = status
                created_team_id = test_result.get('execution_context', {}).get('created_team_id')
            elif operation == 'Edit':
                edit_status = status
    
    assert created_team_id, "Create operation must return a team ID"
    assert create_status == 'PASSED', f"Create failed: {create_status}"
    assert edit_status == 'PASSED', f"Edit failed: {edit_status}"
    
    return {
        'team_id': created_team_id,
        'create_status': create_status,
        'edit_status': edit_status
    }


def test_edit_updates_team_name_and_logs_history(create_then_edit_result):
    """
    Verify Edit operation successfully updated team and logged history.
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
    assert validateSchdGrpHistoryExists(team_id, TEST_USER_ID), \
        "History should be logged"
    
    # Count edit entries (should have 3: identity, allocations, miscellaneous)
    edit_entries = [h for h in history if h.get('operation') == 'edit']
    assert len(edit_entries) >= 3, \
        f"Should have at least 3 edit history entries, got {len(edit_entries)}"
    
    print(f"✅ SUCCESS: Team {team_id} edited successfully with {len(edit_entries)} history entries")

    