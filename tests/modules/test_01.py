from tests.helpers.sp_test_utils import test_stored_procedures
from tests.modules.schGroup_output_validator import getSchdGrpDetails, validateSchdGrpActive
from tests.enums.test_enums import TestCaseType

# Run test and get results
result = test_stored_procedures(
    'usp_CreateUpdateSchedulingTeam',
    TestCaseType.POSITIVE,
    'createSchdGroup_testData',
)

# Query created team
team = getSchdGrpDetails(result['created_team_id'])

if validateSchdGrpActive(result['created_team_id']):
    assert True, " Scheduling group was created and is active"
else:
    assert False, " Scheduling group was created but is not active"

