import pytest
from test_engine_layer.runner import run_stored_procedures, run_stored_procedures_from_csv
from validation_layer.preseed_validator import verify_preseed_exists
from validation_layer.modules.schGroup_validator import (
    getSchdGrpDetails,
    validateSchdGrpActive,
    getSchdGrpHistory,
    validateSchdGrpHistoryExists,
    validateUserCanAccessTeam
)

TEST_USER_ID = 10201  # Fixed test user (creator)
AREA_ADMIN_NEWS_ID = 10201  # areaAdmin_News - can only access News division teams
NEWS_DIVISION_ID = 6  # News division ID 

@pytest.fixture
def created_team_id(db_transaction, request):
    # ensure required reference rows exist (user, division, etc.)
    # the SQL files contain SELECT checks only; they should not perform inserts
   
    verify_preseed_exists(request.fspath, 'createSchdGroup_user.sql')
    verify_preseed_exists(request.fspath, 'createSchdGroup_division.sql')

    # execute stored procedures from keyword-driven CSV
    # Auto-discovery scaffold framework - NO ARGUMENTS NEEDED!
    # Reads data_layer/test_data/keyword_driven_tests.csv
    # Identifies module names and loads matching templates automatically
    execute_result = run_stored_procedures_from_csv()
    
    # Extract team id from results structure
    # execute_result = {total_tests, passed, failed, skipped, 'results': {module_name: [test_results]}}
    all_results = execute_result.get('results', {})
    for module_name, test_results in all_results.items():
        for test_result in test_results:
            if test_result.get('status') == 'passed':
                # Extract from chain output - chain_data contains output_mapping results
                result_data = test_result.get('result', {})
                if isinstance(result_data, dict):
                    # Check in chain_data first (output of the chain execution)
                    chain_data = result_data.get('chain_data', {})
                    tid = chain_data.get('created_team_id')
                    if tid:
                        return tid
    
    # If no team id found, raise assertion error
    assert False, "Creation should return a valid team id"


# add one test function to validate the created team
def test_validate_created_team(created_team_id):
    # Validate team details
    details = getSchdGrpDetails(created_team_id)
    assert details, "Team details should be returned"
    assert details.get('schedulingTeamId') == created_team_id, "Returned team ID should match created team ID"
    
    # Validate team is active
    assert validateSchdGrpActive(created_team_id), "Created team should be active"
    
    # Validate team history exists
    history = getSchdGrpHistory(created_team_id, TEST_USER_ID)
    assert history, "Team history should be returned"
    assert validateSchdGrpHistoryExists(created_team_id, TEST_USER_ID), "Team history should exist"
    
    # Validate test user can access the team
    assert validateUserCanAccessTeam(created_team_id, TEST_USER_ID), "Test user should have access to the created team"

