from tests.helpers.sp_test_utils import test_stored_procedures
from tests.helpers.testcase_output_validator import (
    getSchdGrpDetails,
    validateSchdGrpActive,
)
from tests.enums.test_enums import TestCaseType

# Run test and get results
result = test_stored_procedures(
    'usp_CreateUpdateSchedulingTeam',
    TestCaseType.POSITIVE,
    'createSchdGroup_testData',
)

# Query created team
team = getSchdGrpDetails(result['created_team_id'])


print("\nCreated Scheduling Team Details:")
for key, value in team.items():
    print(f"  {key}: {value}")

