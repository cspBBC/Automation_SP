import pytest

from tests.helpers.sp_test_utils import run_stored_procedures
from tests.modules.schGroup_output_validator import (
    getSchdGrpDetails,
    validateSchdGrpActive,
    getSchdGrpHistory,
    validateSchdGrpHistoryExists,
)
from tests.enums.test_enums import TestCaseType

TEST_USER_ID = 10201  # Fixed test user

@pytest.fixture
def created_team_id(db_transaction, request):
    # ensure required reference rows exist (user, division, etc.)
    # the SQL files contain SELECT checks only; they should not perform inserts
    from tests.helpers.preseed_utils import verify_preseed_exists
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


def test_history_and_create(created_team_id):
    # query the team
    team = getSchdGrpDetails(created_team_id)
    assert team, "Team should exist after creation"

    history = getSchdGrpHistory(created_team_id, TEST_USER_ID)
    assert validateSchdGrpHistoryExists(created_team_id, TEST_USER_ID, expected_count=3)
    assert any('created' in r.get('History', '').lower() for r in history)

    # all verifications successful, no explicit cleanup needed due to transactional isolation


def test_active_flag(created_team_id):
    assert validateSchdGrpActive(created_team_id)
