
from tests.helpers.sp_test_utils import test_stored_procedures
from tests.enums.test_enums import  TestCaseType

#first test run, we will just run the positive cases for one SP to validate the framework is working end-to-end

test_stored_procedures('usp_CreateUpdateSchedulingTeam', TestCaseType.POSITIVE,"test_inputs1")

