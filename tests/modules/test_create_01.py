import pytest
from test_engine_layer.runner import run_stored_procedures
from validation_layer.preseed_validator import verify_preseed_exists
from validation_layer.modules.schGroup_validator import (
    getSchdGrpDetails,
    validateSchdGrpActive,
    getSchdGrpHistory,
    validateSchdGrpHistoryExists,
    validateUserCanAccessTeam
)
from test_engine_layer.enums import TestCaseType

TEST_USER_ID = 10201  # Fixed test user (creator)
AREA_ADMIN_NEWS_ID = 10201  # areaAdmin_News - can only access News division teams
NEWS_DIVISION_ID = 6  # News division ID 

@pytest.fixture
def created_team_id(db_transaction, request):
    # ensure required reference rows exist (user, division, etc.)
    # the SQL files contain SELECT checks only; they should not perform inserts
   
    verify_preseed_exists(request.fspath, 'createSchdGroup_user.sql')
    verify_preseed_exists(request.fspath, 'createSchdGroup_division.sql')

    # execute stored procedure and return new team id;
    result = run_stored_procedures(
        'usp_CreateUpdateSchedulingTeam',
        TestCaseType.POSITIVE,
        'createSchdGroup_testData',
    )
    tid = result.get('created_team_id')
    assert tid, "Creation should return a valid team id"
    return tid


def test_history_create_update(created_team_id):
    # query the team
    team = getSchdGrpDetails(created_team_id)
    assert team, "Team should exist after creation"

    history = getSchdGrpHistory(created_team_id, TEST_USER_ID)
    assert validateSchdGrpHistoryExists(created_team_id, TEST_USER_ID, expected_count=3)
    assert any('created' in r.get('History', '').lower() for r in history)

    # all verifications successful, no explicit cleanup needed due to transactional isolation


def test_active_flag(created_team_id):
    assert validateSchdGrpActive(created_team_id)
    
# def test_area_admin_news_cannot_access_team(created_team_id):
#     """Area admin for News division cannot access a team created by another user."""
#     can_access = validateUserCanAccessTeam(created_team_id, AREA_ADMIN_NEWS_ID, NEWS_DIVISION_ID)
#     assert not can_access, "News area admin should not be able to access this team"
