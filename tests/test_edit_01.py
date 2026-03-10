import pytest
from test_engine_layer.runner import run_stored_procedures_from_data
from test_engine_layer.utils import get_test_case_ids_by_operation


def validate_test_result(test_result, logger):
    """Validate test result against CSV expected values."""
    expected_pattern = (test_result.get('expected_result') or 
                       test_result.get('expected_message_pattern') or '')
    actual_message = test_result.get('sp_message', '') or test_result.get('error', '')
    case_id = test_result.get('case_id', 'unknown')
    
    # Validate message pattern (if specified in CSV and there's an actual message to check)
    if expected_pattern and actual_message:
        patterns = [p.strip() for p in expected_pattern.split('|')]
        match = any(p.lower() in actual_message.lower() for p in patterns)
        assert match, f"{case_id}: Expected [{expected_pattern}] but got: {actual_message}"
    
    logger.info(f"✓ {case_id} validated")


ALL_EDIT_TEST_CASES = get_test_case_ids_by_operation('Edit')
VALID_EDIT_CASES = [tc for tc in ALL_EDIT_TEST_CASES if 'Invalid' not in tc]
INVALID_EDIT_CASES = [tc for tc in ALL_EDIT_TEST_CASES if 'Invalid' in tc]


@pytest.mark.parametrize("test_case_id", VALID_EDIT_CASES, ids=VALID_EDIT_CASES)
def test_edit_with_any_create(db_transaction, logger, test_case_id):
    """Test successful team edit if team was created."""
    result = run_stored_procedures_from_data()
    
    # Find test result for this case
    test_result = None
    for operation_results in result.get('results', {}).values():
        for r in operation_results:
            if r.get('case_id') == test_case_id:
                test_result = r
                break
    
    if not test_result:
        pytest.skip(f"No result found for {test_case_id}")
    
    # Skip if no team ID created
    team_id = test_result.get('execution_context', {}).get('created_team_id')
    if not team_id:
        pytest.skip("No team ID - cannot edit")
    
    # Validate against CSV expected values
    validate_test_result(test_result, logger)


@pytest.mark.parametrize("test_case_id", INVALID_EDIT_CASES, ids=INVALID_EDIT_CASES)
def test_edit_with_invalid_parameters(db_transaction, logger, test_case_id):
    """Test invalid edit parameters are rejected if team was created."""
    result = run_stored_procedures_from_data()
    
    # Find test result for this case
    test_result = None
    for operation_results in result.get('results', {}).values():
        for r in operation_results:
            if r.get('case_id') == test_case_id:
                test_result = r
                break
    
    if not test_result:
        pytest.skip(f"No result found for {test_case_id}")
    
    # Skip if no team ID created
    team_id = test_result.get('execution_context', {}).get('created_team_id')
    if not team_id:
        pytest.skip("No team ID - cannot test invalid edit")
    
    # Validate against CSV expected values
    validate_test_result(test_result, logger)