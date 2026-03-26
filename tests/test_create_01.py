"""Test Create Operations - Team Creation

Tests SP: usp_CreateUpdateSchedulingTeam
Operation: Create (insert new scheduling team)

Expected Results:
  - Baseline creates succeed with team_id returned
  - Duplicates are rejected (constraint)
  - Invalid parameters are rejected (validation)
"""

import pytest
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import get_test_case_ids_by_operation
from validation_layer.schGroup_validator import getSchdGrpDetails


def validate_test_result(test_result, logger):
    """Validate test result against CSV expected values."""
    expected_pattern = (test_result.get('expected_result') or 
                       test_result.get('expected_message_pattern') or '')
    actual_message = test_result.get('sp_message', '') or test_result.get('error', '')
    case_id = test_result.get('case_id', 'unknown')
    
    if not expected_pattern:
        logger.info(f"✓ {case_id} validated (no expected pattern)")
        return
    
    # Determine if we're expecting an error or success based on expected pattern
    error_keywords = ['invalid', 'error', 'required', 'already exists', 'duplicate', 'failed']
    expects_error = any(kw in expected_pattern.lower() for kw in error_keywords)
    
    if expects_error:
        # For error/validation tests, SP MUST return an error message
        assert actual_message, (f"{case_id}: Expected error [{expected_pattern}] but SP succeeded "
                               f"(no error message returned)")
    
    # If there's an actual message, validate it matches the expected pattern
    if actual_message:
        patterns = [p.strip() for p in expected_pattern.split('|')]
        match = any(p.lower() in actual_message.lower() for p in patterns)
        assert match, f"{case_id}: Expected [{expected_pattern}] but got: {actual_message}"
    
    logger.info(f"✓ {case_id} validated")


ALL_CREATE_TEST_CASES = get_test_case_ids_by_operation('Create')
CREATE_TEST_CASES = [tc for tc in ALL_CREATE_TEST_CASES if 'Duplicate' not in tc and 'invalid' not in tc.lower()]
DUPLICATE_TEST_CASES = [tc for tc in ALL_CREATE_TEST_CASES if 'Duplicate' in tc]
INVALID_TEST_CASES = [tc for tc in ALL_CREATE_TEST_CASES if 'invalid' in tc.lower()]


@pytest.mark.parametrize("test_case_id", CREATE_TEST_CASES, ids=CREATE_TEST_CASES)
def test_create_team(db_transaction, logger, test_case_id):
    """Test successful team creation."""
    result = run_stored_procedures_from_data(filter_test_name=test_case_id)
    test_result = list(result.get('results', {}).values())[0][0]
    
    # Validate against CSV expected values
    validate_test_result(test_result, logger)
    
    # Verify team created in database
    team_id = test_result.get('execution_context', {}).get('created_team_id')
    assert team_id, "Team ID must be returned"
    
    team_details = getSchdGrpDetails(team_id)
    assert team_details.get('schedulingTeamId') == team_id, "Team not found in database"


@pytest.mark.parametrize("test_case_id", DUPLICATE_TEST_CASES, ids=DUPLICATE_TEST_CASES)
def test_create_duplicate_prevention(db_transaction, logger, test_case_id):
    """Test duplicate team creation is rejected."""
    result = run_stored_procedures_from_data()
    test_result = list(result.get('results', {}).values())[0]
    test_result = [r for r in test_result if r.get('case_id') == test_case_id][0]
    
    # Validate against CSV expected values
    validate_test_result(test_result, logger)
    
    status = test_result.get('status', '').upper()
    assert status == 'FAILED', "Duplicate should be rejected"


@pytest.mark.parametrize("test_case_id", INVALID_TEST_CASES, ids=INVALID_TEST_CASES)
def test_create_with_invalid_parameters(db_transaction, logger, test_case_id):
    """Test invalid parameters are rejected."""
    result = run_stored_procedures_from_data(filter_test_name=test_case_id)
    test_result = list(result.get('results', {}).values())[0][0]
    
    # Validate against CSV expected values
    validate_test_result(test_result, logger)
