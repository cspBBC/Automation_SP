import pytest
import os, json

from tests.helpers.sp_test_utils import run_stored_procedures, load_test_inputs
from tests.modules.schGroup_output_validator import (
    getSchdGrpDetails,
    validateSchdGrpActive,
    getSchdGrpHistory,
    validateSchdGrpHistoryExists,
)
from tests.enums.test_enums import TestCaseType

TEST_USER_ID = 10201

@pytest.fixture
def edited_team_id(db_transaction):
    # create team first
    create_res = run_stored_procedures(
        'usp_CreateUpdateSchedulingTeam',
        TestCaseType.POSITIVE,
        'createSchdGroup_testData',
    )
    tid = create_res.get('created_team_id')
    assert tid, "Creation should return a valid team id"

    # prepare and run edit chain using dynamic JSON
    edit_data = load_test_inputs('editSchdGroup_testData')

    def _replace(obj):
        if isinstance(obj, str):
            return obj.format(created_team_id=tid)
        if isinstance(obj, dict):
            return {k: _replace(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_replace(v) for v in obj]
        return obj

    edit_data = _replace(edit_data)
    temp_filename = f"temp_edit_{tid}.json"
    temp_path = os.path.join(os.path.dirname(__file__), temp_filename)
    with open(temp_path, 'w') as f:
        json.dump(edit_data, f, indent=2)

    edit_res = run_stored_procedures(
        'usp_CreateUpdateSchedulingTeam',
        TestCaseType.POSITIVE,
        temp_filename.replace('.json',''),
    )
    try:
        os.remove(temp_path)
    except Exception:
        pass

    # return id (should be same) - cleanup handled by transaction rollback
    yield edit_res.get('created_team_id', tid)


def test_edit_history(edited_team_id):
    history = getSchdGrpHistory(edited_team_id, TEST_USER_ID)
    assert len(history) >= 3
    assert any('updated' in r.get('History','').lower() for r in history[:3])


def test_edit_active(edited_team_id):
    assert validateSchdGrpActive(edited_team_id)