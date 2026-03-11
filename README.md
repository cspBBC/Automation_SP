# Scheduling Platform Validation Framework

## Overview
This is a **keyword-driven test framework** that executes database stored procedures, validates results, and maintains test isolation using transactions. It supports parallel execution and works with multiple data formats (CSV, XLSX, JSON).

---

## Section 1: Detailed Test Execution Walkthrough

### Test Case Example: `test_create_team[Create_New_Schd_Team_01]`

Let's trace **exactly** what happens when you run:
```bash
pytest tests/test_create_01.py::test_create_team[Create_New_Schd_Team_01] -v
```

---

### **Step 0: Before pytest Runs (Test Discovery)**

**What pytest does:**
- Scans `tests/` folder for test files
- Finds `test_create_01.py`
- Reads the parametrized test decorator: `@pytest.mark.parametrize("test_case_id", CREATE_TEST_CASES, ids=CREATE_TEST_CASES)`

**Where does CREATE_TEST_CASES come from?**

📁 **File: [tests/test_create_01.py](tests/test_create_01.py#L12)**
```python
# Line 12
CREATE_TEST_CASES = [tc for tc in get_test_case_ids_by_operation('Create') if 'Duplicate' not in tc]
```

- **Input**: Calls function `get_test_case_ids_by_operation('Create')`
- **Process**: Filters to get only 'Create' operations (removes 'Duplicate' tests)
- **Output**: List like `['Create_New_Schd_Team_01', 'Create_New_Schd_Team_02']` (only enabled ones from test data)

**Where is this function defined?**

📁 **File: [test_engine_layer/utils.py](test_engine_layer/utils.py)**
```python
def get_test_case_ids_by_operation(operation):
    """
    Input:  operation = 'Create' (string)
    Output: ['Create_New_Schd_Team_01', 'Create_New_Schd_Team_02'] (list of test case IDs)
    
    Process:
    1. Calls load_test_data() to read test data file
    2. Filters rows where Executed='yes' AND Operation='Create'
    3. Extracts the 'Test Case ID' column
    4. Returns as list
    """
```

**Where does it load test data from?**

📁 **File: [keyword_driven_tests.csv](keyword_driven_tests.csv)** (or XLSX/JSON)

Current enabled test cases:
```
Module                          | Operation | Test Case ID           | Executed | test_description                  | test_parameters
usp_CreateUpdateSchedulingTeam  | Create    | Create_New_Schd_Team_01| yes      | Create_Team_With_Default_Perms    | {...json...}
usp_CreateUpdateSchedulingTeam  | Create    | Create_Duplicate_Team_01| yes     | Create_Duplicate_Team_Should_Fail | {...json...} (EXCLUDED - has 'Duplicate')
usp_CreateUpdateSchedulingTeam  | Create    | Create_New_Schd_Team_02| no       | Create_Team_For_Edit_Workflow     | {...json...}
usp_CreateUpdateSchedulingTeam  | Edit      | Update_Schd_Team_02    | no       | Edit_Team_From_Create_02          | {...json...}
```

**Result**: `CREATE_TEST_CASES = ['Create_New_Schd_Team_01']` (only enabled, no Duplicates)

pytest now knows it will run the test **once** with parameter `test_case_id = 'Create_New_Schd_Team_01'`

---

### **Step 1: pytest Initialization Hook (`pytest_configure`)**

**When**: Before ANY test runs (immediately after discovery)

**File: [tests/conftest.py](tests/conftest.py)**
```python
def pytest_configure(config):
    """
    Input:  config = pytest configuration object
    
    Process:
    1. Call validate_test_configuration()
    2. Auto-detect number of CPU workers
    3. Set CI/parallel mode
    
    Output: 
    - Either: All validations pass → Framework ready
    - Or: Raises error → pytest exits with code 1 (test doesn't even start)
    """
```

**What happens in validate_test_configuration()?**

📁 **File: [test_engine_layer/utils.py](test_engine_layer/utils.py)**
```python
def validate_test_configuration():
    """
    Input: None (reads from test data file)
    
    Output: Either passes silently OR raises ConfigurationError
    
    3-Part Validation:
    ─────────────────
    
    CHECK 1: Edit Tests Require A Create Test
    ──────────────────────────────────────────
    If any Edit test is enabled (Executed=yes):
        → At least ONE Create test must be enabled
        → If not → Error: "Please enable at least one Create test..."
    
    CHECK 2: Duplicate Tests Require Regular Create
    ───────────────────────────────────────────────
    If Duplicate test is enabled (Executed=yes):
        → At least ONE regular Create (non-Duplicate) must be enabled
        → If not → Error: "Please enable at least one regular Create test..."
    
    CHECK 3: Duplicate Parameters Must Match Baseline Create
    ─────────────────────────────────────────────────────────
    If Duplicate test is enabled:
        → Find first enabled regular Create (baseline)
        → Extract: schedulingTeamName, divisionId from both
        → If they DON'T match → Error with details showing mismatch
    
    Current Example Status: ✅ PASS
    - Create_New_Schd_Team_01: enabled ✓
    - Create_Duplicate_Team_01: enabled + matches Create_New_Schd_Team_01 ✓
    """
```

**In our case**: All validations ✅ PASS → pytest continues to run tests

---

### **Step 2: Test Execution Starts (pytest_runtest_setup)**

**When**: Immediately before the test function runs

**File: [tests/conftest.py](tests/conftest.py)** - Fixture injection
```python
@pytest.fixture
def db_transaction(request):
    """
    Input:  request = pytest request object (provides test metadata)
    
    Output: SQLAlchemy transaction object
    
    What happens:
    1. Establish database connection
    2. START transaction (begin())
    3. Yield control to test function (test runs here)
    4. After test finishes:
       → ROLLBACK transaction (auto-cleanup)
       → Database is back to original state
    
    Why: Isolation! Each test starts with clean database
    """

@pytest.fixture
def logger(request):
    """
    Input:  request = pytest request object
    
    Output: Python logger object (logging.getLogger('sp_validation'))
    
    What this logger does:
    - Writes to file: output/tests/test_create_01.py/.../execution_gw0.log
    - Also prints to console if -v flag used
    - Worker-safe: gw0, gw1, etc. for parallel runs
    """

@pytest.fixture
def output_dir(request):
    """
    Input:  request = pytest request object
    
    Output: Path like 'output/tests/test_create_01.py/test_create_team[Create_New_Schd_Team_01]/'
    
    What it does:
    - Creates unique directory for this test
    - Stores: stdout.txt, stderr.txt, execution logs
    """
```

**These 3 fixtures are injected into test function as parameters:**
```python
def test_create_team(db_transaction, logger, test_case_id):
    # Now test has access to:
    # - db_transaction: Isolated database connection
    # - logger: File + console logging
    # - test_case_id: 'Create_New_Schd_Team_01' (from parametrize)
```

---

### **Step 3: Test Function Executes**

**File: [tests/test_create_01.py#L15-L41](tests/test_create_01.py#L15-L41)**

```python
def test_create_team(db_transaction, logger, test_case_id):
    """Execute Create test case."""
    # test_case_id = 'Create_New_Schd_Team_01'
    
    # Line 19: Get module name
    module = get_module_for_test_case(test_case_id)
    # Input: 'Create_New_Schd_Team_01'
    # Output: 'usp_CreateUpdateSchedulingTeam' (from test data row)
    
    # Line 20: Log start
    logger.info(f"\nExecuting: {test_case_id}")
    # Output: Console + File: "Executing: Create_New_Schd_Team_01"
    
    # Line 22: RUN THE STORED PROCEDURE
    result = run_stored_procedures_from_data(filter_test_name=test_case_id)
    # ⚠️ THIS IS THE BIG ONE - See Step 4 below
```

---

### **Step 4: Run Stored Procedures (Core Logic)**

**File: [test_engine_layer/runner.py](test_engine_layer/runner.py)**

```python
def run_stored_procedures_from_data(filter_test_name=None):
    """
    Input:
    ──────
    filter_test_name = 'Create_New_Schd_Team_01'
    
    Process:
    ────────
    1. Load test data from file
    2. Parse JSON parameters from test_parameters column
    3. Fetch stored procedure name from Module column
    4. Call procedure with parameters
    5. Capture result (status, message, created_id, etc.)
    6. Return nested dictionary
    
    Output:
    ───────
    {
        'results': {
            'usp_CreateUpdateSchedulingTeam': [
                {
                    'case_id': 'Create_New_Schd_Team_01',
                    'status': 'SUCCESS',
                    'message': 'Scheduling Team created',
                    'execution_context': {
                        'created_team_id': 12345
                    }
                }
            ]
        }
    }
    """
```

**Behind the scenes - Step 4a: Load Test Data**

```python
# In run_stored_procedures_from_data():

# 1. Call load_test_data()
data = load_test_data()

# Input: None (auto-detects file: keyword_driven_tests.csv, .xlsx, or .json)
# Output: DataFrame with columns:
#         [Module, Operation, Test Case ID, Executed, test_description, test_parameters]

# 2. Filter by test_case_id
row = data[data['Test Case ID'] == 'Create_New_Schd_Team_01'].iloc[0]

# Extracts:
row['Module']           # 'usp_CreateUpdateSchedulingTeam'
row['test_parameters']  # '{"schedulingTeamName":"tst automation schd grwp11",...}'
```

**Step 4b: Parse Parameters**

```python
# In run_stored_procedures_from_data():

import json

params_json = row['test_parameters']
# Input: '{"schedulingTeamName":"tst automation schd grwp11","divisionId":6,...}'

params_dict = json.loads(params_json)
# Output: Dictionary:
# {
#     'schedulingTeamName': 'tst automation schd grwp11',
#     'divisionId': 6,
#     'isActive': 1,
#     'defaultSicknessHoursAllocation': 1,
#     ... (50+ more parameters)
# }
```

**Step 4c: Call Database Stored Procedure**

```python
# In procedure_executor.py:

def execute_procedure(procedure_name, parameters, db_transaction):
    """
    Input:
    - procedure_name: 'usp_CreateUpdateSchedulingTeam'
    - parameters: {all the fields from JSON}
    - db_transaction: SQLAlchemy connection (in transaction)
    
    Process:
    1. Build SQL: EXECUTE usp_CreateUpdateSchedulingTeam @param1=val1, @param2=val2, ...
    2. Execute on database
    3. Wait for result
    4. Capture return value
    5. Extract created_team_id from output parameters
    
    Output:
    {
        'status': 'SUCCESS',
        'message': 'Scheduling Team created successfully',
        'created_team_id': 12345,  # Generated by database
        'execution_time_ms': 234
    }
    """
```

**What the stored procedure does (Database side):**
```sql
-- usp_CreateUpdateSchedulingTeam
-- Input: schedulingTeamName='tst automation schd grwp11', divisionId=6, ... (50+ params)

PROCEDURE usp_CreateUpdateSchedulingTeam
AS
BEGIN
    -- 1. Validate inputs
    IF EXISTS (SELECT 1 FROM SchedulingTeam 
               WHERE schedulingTeamName = @schedulingTeamName 
               AND divisionId = @divisionId)
        RETURN 'ERROR: Duplicate team name'
    
    -- 2. Insert into database
    INSERT INTO SchedulingTeam (schedulingTeamName, divisionId, ...)
    VALUES (@schedulingTeamName, @divisionId, ...)
    
    -- 3. Get the new ID
    SET @createdTeamId = SCOPE_IDENTITY()
    
    -- 4. Return success
    RETURN 'SUCCESS'
END
```

**Database sends back:**
- `status`: 'SUCCESS'
- `created_team_id`: 12345 (new team created)

---

### **Step 5: Test Validation - Extract Result**

**Back in [tests/test_create_01.py#L24-L26](tests/test_create_01.py#L24-L26)**

```python
result = run_stored_procedures_from_data(filter_test_name=test_case_id)
# result = { 'results': { 'usp_CreateUpdateSchedulingTeam': [...] } }

# Line 24: Extract module results
module_results = list(result.get('results', {}).values())[0]
# Input: result dict
# Output: [{ 'case_id': 'Create_New_Schd_Team_01', 'status': 'SUCCESS', ... }]

# Line 25: Find this specific test result
test_result = next((r for r in module_results if r.get('case_id') == test_case_id), None)
# Input: List of results, looking for specific case_id
# Output: Single result dict:
# {
#     'case_id': 'Create_New_Schd_Team_01',
#     'status': 'SUCCESS',
#     'message': 'Scheduling Team created',
#     'execution_context': { 'created_team_id': 12345 }
# }
```

---

### **Step 6: Test Assertions**

**[tests/test_create_01.py#L27-L34](tests/test_create_01.py#L27-L34)**

```python
# Line 27: Verify result exists
assert test_result, f"No result found for test case '{test_case_id}'"
# Input: test_result dict (from Step 5)
# Check: Is it not None/empty?
# If empty → TEST FAILS with message

# Line 29-30: Extract status
status = test_result.get('status', '').upper()
# Input: test_result dict
# Output: 'SUCCESS'

# Line 31: Extract created team ID
created_team_id = test_result.get('execution_context', {}).get('created_team_id')
# Input: test_result nested dict
# Output: 12345 (integer)

# Line 32: Assertion 1 - Check procedure succeeded
assert status in ['SUCCESS', 'PASSED'], f"Expected success but got {status}: {message}"
# Input: status = 'SUCCESS'
# Check: Is it SUCCESS or PASSED?
# If not → TEST FAILS

# Line 33: Assertion 2 - Check team ID was returned
assert created_team_id, f"Create should return team_id but got: {created_team_id}"
# Input: created_team_id = 12345
# Check: Is it not None/0/empty?
# If empty → TEST FAILS
```

**Status so far**: ✅ Procedure succeeded, team created in database

---

### **Step 7: Database Validation**

**[tests/test_create_01.py#L35-L36](tests/test_create_01.py#L35-L36)**

```python
# Line 35: Query database to verify team exists
team_details = getSchdGrpDetails(created_team_id)

# File: validation_layer/schGroup_validator.py
def getSchdGrpDetails(team_id):
    """
    Input: team_id = 12345
    
    Process:
    1. Execute SQL: SELECT * FROM SchedulingTeam WHERE schedulingTeamId = 12345
    2. Fetch all columns
    3. Return as dictionary
    
    Output:
    {
        'schedulingTeamId': 12345,
        'schedulingTeamName': 'tst automation schd grwp11',
        'divisionId': 6,
        'isActive': 1,
        'defaultSicknessHoursAllocation': 1,
        ... (50+ more columns)
    }
    """

# Line 36: Final assertion
assert team_details.get('schedulingTeamId') == created_team_id, f"Team {created_team_id} not found in DB"

# Input: team_details dict from database
# Check: Does it have the same team_id?
# If not found (None) → TEST FAILS
# If found (12345 == 12345) → ✅ TEST PASSES
```

---

### **Step 8: Logging Results**

**[tests/test_create_01.py#L38](tests/test_create_01.py#L38)**

```python
logger.info(f"✓ Team {created_team_id} created successfully")

# File written to:
# output/tests/test_create_01.py/test_create_team[Create_New_Schd_Team_01]/execution_gw0.log

# Console output (if -v):
# ✓ Team 12345 created successfully
```

---

### **Step 9: Cleanup (Test Teardown)**

**Automatic - via db_transaction fixture**

```python
# After test function finishes (whether PASS or FAIL):

# conftest.py db_transaction fixture:
@pytest.fixture
def db_transaction(request):
    connection.begin()  # Started in Step 2
    yield  # ← test runs here (Steps 3-8)
    # After test:
    connection.rollback()  # ← Database reverts ALL changes
    connection.close()
```

**What this does:**
- ✅ Team 12345 was created in Step 6
- ✅ Team 12345 was verified in database in Step 7
- ✅ After test → `ROLLBACK` → Team 12345 is DELETED from database
- ✅ Database is now in original state (like test never ran)
- ✅ Next test starts with clean database

**Why**: Test isolation! Tests don't interfere with each other.

---

### **Step 10: Test Result Reported**

```
============================= test session starts =============================
...
tests/test_create_01.py::test_create_team[Create_New_Schd_Team_01] PASSED  [ 33%]

- Generated html report: file:///C:/sp_validation/reports/sp_automation_report.html
======================== 1 passed in 2.45s ===========================
```

**Output artifacts created:**
1. ✅ HTML Report: `reports/sp_automation_report.html` (shows all test runs)
2. ✅ Test Output Dir: `output/tests/test_create_01.py/test_create_team[Create_New_Schd_Team_01]/`
   - `stdout.txt` - Captured console output
   - `stderr.txt` - Any errors
   - `execution_gw0.log` - Framework logs

---

## File Dependencies Summary

```
pytest command
    ↓
[tests/conftest.py] pytest_configure() hook
    ├─ Calls: [test_engine_layer/utils.py] validate_test_configuration()
    │   ├─ Reads: [keyword_driven_tests.csv] (test data)
    │   └─ Returns: Pass or ConfigurationError
    ├─ Calls: [test_engine_layer/utils.py] get_test_case_ids_by_operation('Create')
    │   ├─ Reads: [keyword_driven_tests.csv]
    │   └─ Returns: ['Create_New_Schd_Team_01', ...]
    ├─ Parametrizes test with: test_case_id = 'Create_New_Schd_Team_01'
    └─ Injects fixtures: db_transaction, logger, output_dir
        ↓
[tests/test_create_01.py] test_create_team()
    ├─ Calls: [test_engine_layer/utils.py] get_module_for_test_case(test_case_id)
    │   └─ Returns: 'usp_CreateUpdateSchedulingTeam'
    ├─ Calls: [test_engine_layer/runner.py] run_stored_procedures_from_data()
    │   ├─ Calls: [test_engine_layer/utils.py] load_test_data()
    │   │   ├─ Reads: [keyword_driven_tests.csv]
    │   │   └─ Returns: DataFrame with all test data
    │   ├─ Calls: [database_layer/procedure_executor.py] execute_procedure()
    │   │   ├─ Executes: usp_CreateUpdateSchedulingTeam (SQL)
    │   │   ├─ Database: INSERT into SchedulingTeam table
    │   │   └─ Returns: {status, created_team_id, ...}
    │   └─ Returns: Nested result dict with all procedure outputs
    ├─ Calls: [validation_layer/schGroup_validator.py] getSchdGrpDetails(team_id)
    │   ├─ Queries: SELECT * FROM SchedulingTeam WHERE id = team_id
    │   └─ Returns: Team details or None
    └─ Asserts & logs results
        ↓
[tests/conftest.py] db_transaction fixture cleanup
    └─ ROLLBACK: Deletes created team from database
        ↓
HTML Report generated: reports/sp_automation_report.html
```

---

## Key Concepts

| Concept | Purpose | Implementation |
|---------|---------|-----------------|
| **Parametrization** | Run same test with different inputs | `@pytest.mark.parametrize("test_case_id", CREATE_TEST_CASES)` |
| **Fixtures** | Setup/cleanup per test | `db_transaction`, `logger`, `output_dir` |
| **Transaction Isolation** | Each test uses clean DB | `connection.begin()` then `connection.rollback()` |
| **Format Agnostic** | Support CSV/XLSX/JSON | `load_test_data()` auto-detects format |
| **Configuration Validation** | Catch errors early | `pytest_configure()` hook runs first |
| **Parallel Execution** | Run multiple tests simultaneously | pytest-xdist with auto CPU detection |
| **Comprehensive Logging** | Track every step | Worker-safe file + console logging |

---

## To Run Tests

```bash
# Run one specific test
pytest tests/test_create_01.py::test_create_team[Create_New_Schd_Team_01] -v

# Run all Create tests
pytest tests/test_create_01.py -v

# Run all tests in parallel (uses all CPU cores)
pytest tests/ -n auto -v

# Run with detailed logging
pytest tests/ -v -s

---

## Section 2: Data Loading Flow - How Test Data Gets Read

### Function Call Chain: `get_test_case_ids_by_operation('Create')`

Let's trace **exactly** how test data is loaded when pytest calls:
```python
CREATE_TEST_CASES = [tc for tc in get_test_case_ids_by_operation('Create') if 'Duplicate' not in tc]
```

---

### **Step 1: Call Function in [test_engine_layer/utils.py](test_engine_layer/utils.py#L78)**

```python
def get_test_case_ids_by_operation(operation: str, data_file: str = None) -> List[str]:
    """
    Input:
    ──────
    operation = 'Create' (string)
    data_file = None (uses default from config)
    
    Output:
    ───────
    ['Create_New_Schd_Team_01']  (list of test case IDs)
    """
```

**What happens inside:**
- Line 1: Function receives `operation='Create'`
- Line 2: Initializes empty list `test_cases = []`
- Line 3: Calls `load_test_data(data_file)` ← **THIS IS THE KEY CALL**

---

### **Step 2: Call `load_test_data()` - File Discovery**

**File: [test_engine_layer/utils.py](test_engine_layer/utils.py#L63)**

```python
def load_test_data(data_file: str = None) -> Dict:
    """Load test data from CSV/Excel/JSON file.
    
    Args:
        data_file: Optional data file path. Defaults to configured file.
        
    Returns:
        Dict of {module_name: [test_case_rows]}
    """
    from data_loader_factory import TestDataLoader
    
    if data_file is None:
        data_file = DataConfig.DEFAULT_TEST_DATA_FILE
        # DEFAULT_TEST_DATA_FILE = 'keyword_driven_tests.csv'
    
    return TestDataLoader.load(data_file)
    # ↑ Calls the factory loader
```

**Process:**
```
Input: data_file = None
  ↓
Load from config: DEFAULT_TEST_DATA_FILE = 'keyword_driven_tests.csv'
  ↓
Call: TestDataLoader.load('keyword_driven_tests.csv')
```

---

### **Step 3: TestDataLoader - Smart Format Detection**

**File: [data_loader_factory/factory.py](data_loader_factory/factory.py)**

```python
class TestDataLoader:
    """
    Universal test data loader for various formats.
    
    Auto-detects format from file extension and uses the appropriate loader.
    Supports JSON, CSV (with automatic schema detection), and Excel (XLSX/XLS) formats.
    """
    
    # ┌─────────────────────────────────────────────────────┐
    # │  _LOADERS Dictionary - Maps Extension to Loader    │
    # └─────────────────────────────────────────────────────┘
    
    _LOADERS = {
        '.json': JSONLoader,
        '.csv': CSVLoader,
        '.xlsx': ExcelLoader,
        '.xls': ExcelLoader,
    }
    
    @staticmethod
    def load(file_path: str, format: str = None, loader_type: str = None) -> Dict[str, Any]:
        """
        Input:
        ──────
        file_path = 'keyword_driven_tests.csv'
        format = None (auto-detect)
        loader_type = None (deprecated, kept for backward compatibility)
        
        Output:
        ───────
        {
            'usp_CreateUpdateSchedulingTeam': [
                {
                    'case_id': 'Create_New_Schd_Team_01',
                    'operation': 'Create',
                    'executed': True,
                    'module': 'usp_CreateUpdateSchedulingTeam',
                    ...
                },
                {
                    'case_id': 'Create_Duplicate_Team_01',
                    'operation': 'Create',
                    'executed': True,
                    ...
                },
                ...
            ]
        }
        """
```

**What `@staticmethod` means:**
```
@staticmethod
def load(file_path: str) -> Dict:
    pass

┌──────────────────────────────────────────────────┐
│ @staticmethod MEANS:                             │
│                                                   │
│ 1. NOT a class method                            │
│ 2. NOT an instance method                        │
│ 3. CAN be called without creating an instance   │
│ 4. NO access to 'self' or 'cls'                 │
│ 5. PURE FUNCTION inside a class                 │
│                                                   │
│ Usage:                                           │
│ ✅ TestDataLoader.load(file)     [Class name]   │
│ ❌ obj.load(file)               [Need instance] │
│ ❌ self.load(file)              [Inside class]  │
└──────────────────────────────────────────────────┘
```

**Process inside TestDataLoader.load():**

```python
# Line 1: Detect file extension
if format:
    # Explicit format provided
    ext = f".{format.lower()}"
else:
    # Auto-detect from file path
    ext = os.path.splitext(file_path)[1].lower()
    # For 'keyword_driven_tests.csv':
    # ext = '.csv'

# Line 2: Get the appropriate loader from _LOADERS
loader_class = _LOADERS.get(ext)

# For '.csv':
# loader_class = CSVLoader

# Line 3: Call the loader's load() method
return loader_class.load(file_path)

# Calls: CSVLoader.load('keyword_driven_tests.csv')
```

---

### **Step 4: CSVLoader - File Reading & Schema Detection**

**File: [data_loader_factory/loaders/csv_loader.py](data_loader_factory/loaders/csv_loader.py)**

```python
class CSVLoader(BaseLoader):
    """Load test data from CSV files with automatic schema detection.
    
    Auto-detects schema and supports both:
    - Keyword-driven format (Module/Operation/Test Case ID/etc.)
    - Generic format (sp_name)
    """
    
    @staticmethod
    def load(file_path: str) -> Dict[str, Any]:
        """
        Input:
        ──────
        file_path = 'keyword_driven_tests.csv'
        """
        
        # Step 4a: Locate the file
        if not os.path.isabs(file_path):
            # Build absolute path from project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            #                  ↑ data_loader_factory
            #                        ↑ sp_validation
            
            file_path = os.path.join(project_root, file_path)
            # Result: C:\sp_validation\keyword_driven_tests.csv
        
        # Step 4b: Verify file exists
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Test data file not found: {file_path}")
        
        # Step 4c: Read CSV file
        logger.info(f"Using CSVLoader for: {file_path}")
        logger.info(f"Loading CSV test data from: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f)
                # DictReader uses first row (headers) as keys
                # Headers: Module, Operation, Test Case ID, Executed, test_description, test_parameters
                
                rows = list(csv_reader)
                # rows = [
                #     {'Module': 'usp_CreateUpdateSchedulingTeam',
                #      'Operation': 'Create',
                #      'Test Case ID': 'Create_New_Schd_Team_01',
                #      'Executed': 'yes',
                #      'test_description': 'Create_Team_With_Default_Permissions',
                #      'test_parameters': '{"schedulingTeamName":"...", ...}'},
                #     {'Module': 'usp_CreateUpdateSchedulingTeam',
                #      'Operation': 'Create',
                #      'Test Case ID': 'Create_Duplicate_Team_01',
                #      'Executed': 'yes',
                #      ...},
                #     ...
                # ]
        
        # Step 4d: Auto-detect schema
        schema_type = _detect_schema(rows)
        # schema_type = 'keyword-driven'
        
        # Step 4e: Transform to standard format
        if schema_type == 'keyword-driven':
            data = _transform_keyword_driven(rows)
        else:
            data = _transform_generic(rows)
        
        logger.info(f"Detected schema: {schema_type}")
        logger.info(f"Successfully loaded test data from {file_path}")
        
        return data
        # Result: 
        # {
        #     'usp_CreateUpdateSchedulingTeam': [
        #         {
        #             'case_id': 'Create_New_Schd_Team_01',
        #             'operation': 'Create',
        #             'executed': True,  [CONVERTED from 'yes']
        #             'module': 'usp_CreateUpdateSchedulingTeam',
        #             'description': 'Create_Team_With_Default_Permissions',
        #             'parameters': {...}
        #         },
        #         ...
        #     ]
        # }
```

**Inside _transform_keyword_driven():**

```python
def _transform_keyword_driven(rows):
    """
    Transform keyword-driven CSV rows to standard format.
    
    Input row (from CSV):
    ────────────────────
    {
        'Module': 'usp_CreateUpdateSchedulingTeam',
        'Operation': 'Create',
        'Test Case ID': 'Create_New_Schd_Team_01',
        'Executed': 'yes',
        'test_description': 'Create_Team_With_Default_Permissions',
        'test_parameters': '{"schedulingTeamName":"...", ...}'
    }
    
    Output row (standardized):
    ──────────────────────────
    {
        'case_id': 'Create_New_Schd_Team_01',
        'operation': 'Create',
        'module': 'usp_CreateUpdateSchedulingTeam',
        'executed': True,  [STRING 'yes' → BOOLEAN True]
        'description': 'Create_Team_With_Default_Permissions',
        'parameters': {'schedulingTeamName': '...', ...}  [JSON STRING → DICT]
    }
    """
    
    data = {}
    
    for row in rows:
        module = row.get('Module', '').strip()
        
        # Create module entry if needed
        if module not in data:
            data[module] = []
        
        # Parse parameters JSON
        params_str = row.get('test_parameters', '{}')
        try:
            parameters = json.loads(params_str)
        except json.JSONDecodeError:
            parameters = {}
        
        # Convert 'Executed' string to boolean
        executed_str = row.get('Executed', 'no').strip().lower()
        executed = executed_str == 'yes'
        
        # Build standardized row
        transformed_row = {
            'case_id': row.get('Test Case ID', '').strip(),
            'operation': row.get('Operation', '').strip(),
            'module': module,
            'executed': executed,
            'description': row.get('test_description', ''),
            'parameters': parameters
        }
        
        data[module].append(transformed_row)
    
    return data
```

---

### **Step 5: Back to get_test_case_ids_by_operation() - Filter Results**

**Back in [test_engine_layer/utils.py](test_engine_layer/utils.py#L78)**

```python
def get_test_case_ids_by_operation(operation: str, data_file: str = None) -> List[str]:
    """
    After Step 4, we have loaded data dictionary
    """
    
    # Step 5a: Load data (Steps 2-4)
    test_data = load_test_data(data_file)
    # Result:
    # {
    #     'usp_CreateUpdateSchedulingTeam': [
    #         {'case_id': 'Create_New_Schd_Team_01', 'operation': 'Create', 'executed': True, ...},
    #         {'case_id': 'Create_Duplicate_Team_01', 'operation': 'Create', 'executed': True, ...},
    #         {'case_id': 'Create_New_Schd_Team_02', 'operation': 'Create', 'executed': False, ...},
    #         {'case_id': 'Update_Schd_Team_02', 'operation': 'Edit', 'executed': False, ...}
    #     ]
    # }
    
    # Step 5b: Initialize result list
    test_cases = []
    
    # Step 5c: Iterate through all modules
    for module_name, cases in test_data.items():
        # First iteration: module_name = 'usp_CreateUpdateSchedulingTeam'
        # cases = [all rows for that module]
        
        # Step 5d: Iterate through cases in this module
        for row in cases:
            # Iteration 1: row = {'case_id': 'Create_New_Schd_Team_01', 'operation': 'Create', 'executed': True, ...}
            # Iteration 2: row = {'case_id': 'Create_Duplicate_Team_01', 'operation': 'Create', 'executed': True, ...}
            # Iteration 3: row = {'case_id': 'Create_New_Schd_Team_02', 'operation': 'Create', 'executed': False, ...}
            # Iteration 4: row = {'case_id': 'Update_Schd_Team_02', 'operation': 'Edit', 'executed': False, ...}
            
            # Step 5e: Extract fields from row
            test_name = row.get('case_id', '').strip()
            op = row.get('operation', '').strip()
            executed_raw = row.get('executed', False)
            
            # Step 5f: Convert string to boolean (if needed)
            if isinstance(executed_raw, str):
                executed = executed_raw.lower() == 'true'
            else:
                executed = bool(executed_raw)
            
            # Step 5g: Check if matches criteria
            if op.lower() == operation.lower() and executed:
                # For operation='Create' and executed=True:

---

## Section 3: Framework Architecture - Complete Guide for New Users

### Overview
This section explains the **complete end-to-end flow** of the Scheduling Platform Validation Framework - from folder structure, components, dependencies, execution, to report generation.

---

### 📁 **Part 1: Folder Structure & Purpose**

```
c:\sp_validation\
├── keyword_driven_tests.csv          # Test data source (Create/Update/Delete test cases)
├── pytest.ini                        # pytest configuration (test discovery, logging)
├── requirements.txt                  # Python dependencies (pytest, sqlalchemy, etc)
├── README.md                         # This file
│
├── config/                           # Configuration layer
│   ├── __init__.py
│   └── config.py                     # DB connection strings, environments, constants
│
├── data_layer/                       # Test data templates
│   ├── __init__.py
│   └── test_data/
│       └── usp_CreateUpdateSchedulingTeam/  # Folder per stored procedure
│           ├── preseed_data/         # Pre-setup test data needed before running test
│           └── template_data/        # Empty test team templates for param override
│
├── data_loader_factory/              # Data loading logic
│   ├── __init__.py
│   ├── testDataLoaderfactory.py      # Factory pattern - loads data by file type
│   ├── fileLoader.py                 # Abstract base loader
│   └── loaders/
│       ├── base_loader.py            # Parent class for all loaders
│       ├── csv_loader.py             # Load .csv files
│       ├── excel_loader.py           # Load .xlsx files
│       ├── json_loader.py            # Load .json files
│       └── keyword_driven_loader.py  # Load keyword-driven test data
│
├── database_layer/                   # Database interaction layer
│   ├── __init__.py
│   ├── connection.py                 # Establish DB connections
│   ├── procedure_executor.py         # Execute stored procedures (main SP calling)
│   ├── chain_executor.py             # Execute multiple SPs in sequence
│   ├── transaction_manager.py        # Begin/commit/rollback transactions
│   └── normalizer.py                 # Normalize/clean SP output
│
├── validation_layer/                 # Result validation
│   ├── __init__.py
│   ├── generic_validators.py         # Common validation rules (not null, type check, etc)
│   ├── preseed_validator.py          # Validate pre-setup data
│   └── schGroup_validator.py         # Domain-specific validators
│
├── test_engine_layer/                # Test execution engine
│   ├── __init__.py
│   ├── builder.py                    # Build test cases from test data
│   ├── parameter_manager.py          # Extract/parse test parameters
│   ├── runner.py                     # Orchestrate test execution
│   ├── template_transformer.py       # Override template with test params
│   └── utils.py                      # Utility functions (file loading, filtering, etc)
│
├── tests/                            # Actual pytest test files
│   ├── __init__.py
│   ├── conftest.py                   # pytest fixtures & hooks (fixtures: db_transaction, logger, output_dir)
│   ├── test_create_01.py             # Create operation tests
│   └── test_edit_01.py               # Edit operation tests
│
└── output/                           # Test execution results
    ├── reports/
    │   └── sp_automation_report.html # Final HTML report
    └── tests/
        ├── test_create_01.py/
        │   └── test_create_team[Create_New_Schd_Team_01]/  # Per-test folder
        │       ├── execution_gw0.log                       # Execution logs
        │       ├── stdout.txt                              # Captured stdout
        │       └── stderr.txt                              # Captured stderr
        └── test_edit_01.py/
            └── ...
```

---

### 🔧 **Part 2: Core Components & Their Roles**

#### **Component 1: Test Data File (`keyword_driven_tests.csv`)**
```
Purpose: Define WHAT tests to run (keyword-driven approach)
Format: CSV with columns:
  - Module: Stored procedure name (e.g., usp_CreateUpdateSchedulingTeam)
  - Operation: Create, Edit, Delete, etc.
  - Test Case ID: Unique identifier (e.g., Create_New_Schd_Team_01)
  - Executed: yes/no (enable/disable test)
  - expected_result: What should succeed/fail
  - test_description: Human-readable description
  - test_parameters: JSON with all SP input parameters

Example Row:
  usp_CreateUpdateSchedulingTeam | Create | Create_New_Schd_Team_01 | yes | record inserted successfully | Create baseline team | {"schedulingTeamName":"team1",...}
```

**Key Logic: Test Dependency**
```
- Edit tests CAN ONLY RUN if their corresponding Create succeeded
- During execution: If Create_New_Schd_Team_01 succeeds and generates a team ID:
  → Edit_New_Schd_Team_01 automatically has that team ID injected
  → Both execute in same database transaction
- If Create fails → Edit is NOT executed (no valid ID)
```

---

#### **Component 2: Data Layer (`data_loader_factory/`)**

**What it does**: Reads test data from different file formats

**How it works**:
```
1. testDataLoaderfactory.py:
   - Detects file type (.csv, .xlsx, .json)
   - Selects appropriate loader

2. Specific loaders (csv_loader.py, excel_loader.py, etc.):
   - Read raw file → Dictionary format
   - Normalize field names (lowercase, strip spaces)
   - Return list of test case dictionaries

3. keyword_driven_loader.py:
   - Special loader for "keyword-driven tests"
   - Extracts test cases marked as Executed='yes'
   - Groups by Module & Operation
```

**Example Output**:
```python
{
  'usp_CreateUpdateSchedulingTeam': [
    {'Test Case ID': 'Create_New_Schd_Team_01', 'Operation': 'Create', 'Executed': True, 'test_parameters': {...}},
    {'Test Case ID': 'Create_Duplicate_Team_01', 'Operation': 'Create', 'Executed': True, ...},
    {'Test Case ID': 'Edit_New_Schd_Team_01', 'Operation': 'Edit', 'Executed': False, ...},
  ]
}
```

---

#### **Component 3: Database Layer (`database_layer/`)**

**Subcomponent 3a: Connection (`connection.py`)**
```python
def connect(connection_string, use_autoload_schema=True):
    """
    Input: Database connection string
    Output: SQLAlchemy Engine & MetaData objects
    Purpose: Establish connection to SQL Server
    """
```

**Subcomponent 3b: Transaction Manager (`transaction_manager.py`)**
```python
with db_transaction:  # BEGIN TRANSACTION
    # Execute SP
    result = procedure_executor.execute(sp_name, sp_params)
    # If test passes:
    db_transaction.commit()  # COMMIT
    # If test fails:
    db_transaction.rollback()  # ROLLBACK - database unchanged
```

**Why**: Test isolation! Each test starts with fresh database state.

**Subcomponent 3c: Procedure Executor (`procedure_executor.py`)**
```python
def execute_procedure(sp_name, input_params, db_connection):
    """
    Input:
      - sp_name: 'usp_CreateUpdateSchedulingTeam' (stored proc name)
      - input_params: {'schedulingTeamName': 'team1', 'divisionId': 6, ...}
      - db_connection: SQLAlchemy connection
    
    Process:
      1. Create callable: connection.run_sync(lambda c: c.execute(...))
      2. Pass parameters to SP
      3. SP executes in SQL Server
      4. Capture return code & output parameters
    
    Output:
      {
        'return_code': 1 (success) or 0 (failure),
        'new_team_id': 123 (if Create succeeded),
        'message': 'record inserted successfully',
        'affected_rows': 1
      }
    """
```

**Subcomponent 3d: Chain Executor (`chain_executor.py`)**
```python
# Execute Create then Edit in same transaction:
result1 = execute_procedure('usp_CreateUpdateSchedulingTeam', create_params)
# SP generates new_team_id = 123

result2 = execute_procedure('usp_CreateUpdateSchedulingTeam', edit_params)
# Edit_params uses new_team_id from result1
# Both succeed or both rollback
```

---

#### **Component 4: Validation Layer (`validation_layer/`)**

```python
def validate_result(result, expected_result, validators):
    """
    Input:
      - result: SP output (what actually happened)
      - expected_result: 'record inserted successfully' (what should happen)
      - validators: [check_return_code, check_message, check_row_count]
    
    Process:
      1. Run each validator
      2. Check: return_code == 1? message matches? rows inserted? etc.
      3. Collect all failures
    
    Output: Pass or Fail with detailed error messages
    """
```

**Example Validators**:
- `generic_validators.py`: Is return_code 0? Is message not null?
- `schGroup_validator.py`: Is divisionId valid? Does team already exist?

---

#### **Component 5: Test Engine (`test_engine_layer/`)**

**Subcomponent 5a: Builder (`builder.py`)**
```python
def build_test_cases(test_data):
    """
    Convert raw test data to runnable test cases
    Input: {'Create_New_Schd_Team_01': {'test_parameters': '{"schedulingTeamName":"team1",...}'}}
    Output: [TestCase(id='...', operation='...', params={...}), ...]
    """
```

**Subcomponent 5b: Parameter Manager (`parameter_manager.py`)**
```python
def extract_test_parameters(json_string):
    """
    Input: '{"schedulingTeamName":"team1","divisionId":6,...}'
    Output: {'schedulingTeamName': 'team1', 'divisionId': 6, ...} (Python dict)
    Purpose: Parse JSON parameters from CSV
    """
```

**Subcomponent 5c: Template Transformer (`template_transformer.py`)**
```python
def merge_template_with_overrides(template, test_params):
    """
    Purpose: Allow parameterized tests (override template values)
    Input:
      template: {'schedulingTeamName': 'default_team', 'divisionId': 1, ...}
      test_params: {'schedulingTeamName': 'custom_team'} (only overrides)
    Output: {'schedulingTeamName': 'custom_team', 'divisionId': 1, ...} (merged)
    """
```

**Subcomponent 5d: Utils (`utils.py`)**
```python
def get_test_case_ids_by_operation(operation):
    """Filter test cases by operation (Create/Edit/Delete) and Executed=yes"""

def load_test_data():
    """Load from CSV/XLSX/JSON and normalize"""

def get_test_case(case_id):
    """Fetch specific test case by ID"""
```

---

### 🧪 **Part 3: Complete Test Execution Flow (E2E)**

#### **Step 1: User runs pytest**
```bash
cd c:\sp_validation
pytest tests/test_create_01.py -v --count=5
```

#### **Step 2: Test Discovery**
```
pytest reads:
  - Scans tests/ folder
  - Finds test_create_01.py
  - Calls get_test_case_ids_by_operation('Create')
  - Gets: ['Create_New_Schd_Team_01', 'Create_Duplicate_Team_01', 'Create_LongText_06']
  - Creates parametrized test 3 times (one for each)
```

#### **Step 3: pytest_configure (conftest.py)**
```
- Validates config:
  - At least 1 Create test enabled? ✓
  - Create & Duplicate params match? ✓
  - Database connection works? ✓
- If fails → pytest exits with error
- If passes → Continue
```

#### **Step 4: Database Connection**
```
connection.py:
  Connection string: Server=SQLSERVER;Database=TestDB;Trusted_Connection=True
  → SQLAlchemy Engine created
  → Metadata loaded (table schemas, SP definitions)
```

#### **Step 5: Test Execution (per test case)**
```
For test_case_id = 'Create_New_Schd_Team_01':

  5.1. Load test data
       - CSV row: Module, Operation, Test Case ID, Executed, expected_result, test_parameters
  
  5.2. Extract parameters
       - JSON: {"schedulingTeamName":"team1","divisionId":6,...}
       → Python dict
  
  5.3. Start transaction
       - transaction_manager.begin()  # Database snapshot
  
  5.4. Execute stored procedure
       - SP: usp_CreateUpdateSchedulingTeam
       - Params: {schedulingTeamName: 'team1', divisionId: 6, task: 'create', ...}
       - Output: {return_code: 1, new_team_id: 456, message: 'record inserted successfully'}
  
  5.5. Validate result
       - Expected: 'record inserted successfully'
       - Actual: Output message
       - Validators run: return_code==1? message matches? ✓
  
  5.6. Check database side effects
       - Query: SELECT * FROM SchedulingTeams WHERE TeamID = 456
       - Assert: Row exists + data matches params
  
  5.7. Log results
       - execution_gw0.log: "PASS: Create_New_Schd_Team_01"
       - output_dir/stdout.txt: Captured print statements
  
  5.8. Cleanup
       - transaction_manager.rollback()  # Restore database
       - Close resources
```

#### **Step 6: Edit Tests (if Create succeeded)**
```
If Create_New_Schd_Team_01 PASSED:
  - new_team_id = 456 (extracted)
  - Edit_New_Schd_Team_01 parameters are injected with this ID
  - Edit runs in SAME transaction with Create
  - If Edit fails → entire transaction rolls back
  
If Create_New_Schd_Team_01 FAILED:
  - Edit_New_Schd_Team_01 is SKIPPED (no valid team ID)
```

#### **Step 7: Report Generation**
```
After all tests complete:

  7.1. Collect results
       - Test IDs, statuses (pass/fail), execution times
       - Error messages, assertion failures
  
  7.2. Generate HTML report
       - pytest-html plugin creates sp_automation_report.html
       - Shows: Summary (3 passed, 1 failed), pie charts, test details
  
  7.3. Output structure
       output/
       ├── reports/
       │   └── sp_automation_report.html      # Main report (open in browser)
       └── tests/
           └── test_create_01.py/
               ├── test_create_team[Create_New_Schd_Team_01]/
               │   ├── execution_gw0.log      # Detailed logs
               │   ├── stdout.txt
               │   └── stderr.txt
               └── ...
```

---

### 🚀 **Part 4: How to Execute Tests**

#### **Option 1: Run all tests**
```bash
pytest tests/ -v
```
Output: Runs all test files (test_create_01.py, test_edit_01.py, etc.)

#### **Option 2: Run specific test file**
```bash
pytest tests/test_create_01.py -v
```
Output: Only CREATE operation tests

#### **Option 3: Run specific test case**
```bash
pytest tests/test_create_01.py::test_create_team[Create_New_Schd_Team_01] -v
```
Output: Only this one test case

#### **Option 4: Run with parallel workers**
```bash
pytest tests/ -v -n 4  # Use 4 CPU cores
```
Output: Tests run in parallel (thread-safe, each has own transaction)

#### **Option 5: Check test report**
```bash
start output/reports/sp_automation_report.html  # Open HTML report
```

---

### 🔗 **Part 5: Test Dependency Logic**

#### **The Simple Rule**
```
Edit can only happen if Create succeeded AND generated an ID
```

#### **How It Works**

**Scenario 1: Create succeeds**
```
Test flow:
  1. Create_New_Schd_Team_01 runs
     - SP: usp_CreateUpdateSchedulingTeam(task='create', ...)
     - Result: return_code=1, new_team_id=456 ✓
  
  2. Because Create succeeded:
     - Extract new_team_id=456
     - Inject into Edit_New_Schd_Team_01 parameters
     - Edit runs with this team ID
     - Both in SAME transaction
```

**Scenario 2: Create fails**
```
Test flow:
  1. Create_Invalid_Values_02 runs
     - SP: usp_CreateUpdateSchedulingTeam(divisionId='ABC', ...) ❌ (invalid type)
     - Result: return_code=0 (error), no new_team_id
  
  2. Because Create failed:
     - Edit tests referencing this Create are SKIPPED
     - (No valid team ID to update)
  
  3. Validation passes:
     - expected_result='Error converting data type' matches actual error ✓
```

**Scenario 3: Duplicate prevention**
```
Test flow:
  1. Create_New_Schd_Team_01 runs (first time)
     - schedulingTeamName='team_xyz'
     - Result: ✓ Created (new_team_id=456)
  
  2. Create_Duplicate_Team_01 runs (same team name)
     - schedulingTeamName='team_xyz' (SAME as above)
     - SP rejects duplicate
     - Result: return_code=0, error='already exists'
     - expected_result='already exists' matches ✓
```

#### **No Cross-Test Dependencies**
```
❌ BAD (avoid):
  - Create_Test_1 depends on Create_Test_2 succeeding
  - Can't run tests independently
  - Brittle, hard to debug

✓ GOOD (current design):
  - Each Create test is independent
  - Edit depends only on ITS OWN Create (in same transaction)
  - All tests runnable in any order
  - Parallel execution safe
```

---

### 📊 **Part 6: Report Generation Details**

#### **What the Report Shows**

```html
<!-- output/reports/sp_automation_report.html -->
┌─────────────────────────────────────────┐
│ Test Summary                             │
│ ─────────────────────────────────────── │
│ Total: 15 tests                         │
│ Passed: 11 (73%)                        │
│ Failed: 3 (20%)                         │
│ Skipped: 1 (7%)                         │
└─────────────────────────────────────────┘

Breakdown:
  ✓ Create_New_Schd_Team_01: PASSED (1.23s)
  ✓ Edit_New_Schd_Team_01: PASSED (0.87s)
  ✗ Create_Invalid_Values_02: PASSED (expected failure) (0.92s)
    • Expected 'Error converting data type'
    • Got 'Error converting data type' ✓
  ✓ Create_LongText_06: PASSED (1.05s)
  ...
```

#### **How Report is Generated**

```python
# After all tests complete:
1. pytest hooks into result callback
2. Collects: test_ids, statuses, durations, error messages
3. Calls: pytest-html plugin
4. Generates: sp_automation_report.html
5. File location: output/reports/sp_automation_report.html
```

#### **View Report**
```bash
# Windows
start output\reports\sp_automation_report.html

# Linux/Mac
open output/reports/sp_automation_report.html
```

---

### 🔍 **Part 7: Key Configuration Files**

#### **`pytest.ini`**
```ini
[pytest]
testpaths = tests/
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --html=output/reports/sp_automation_report.html --self-contained-html
log_cli = true
log_cli_level = INFO
```
Purpose: Tell pytest where tests are, how to discover them, what plugins to use

#### **`config/config.py`**
```python
DATABASE_URLS = {
    'dev': 'mssql+pyodbc://SERVER/TestDB?trusted_connection=yes',
    'staging': '...',
    'prod': '...'
}

TEST_DATA_FILE_PATH = 'keyword_driven_tests.csv'
TEST_DATA_BACKUP_PATH = 'data_layer/test_data/'
```
Purpose: Centralize configuration (change DB → edit here once)

#### **`requirements.txt`**
```
pytest==7.4.0
sqlalchemy==2.0.21
pandas==2.0.3
openpyxl==3.1.2
pytest-html==3.2.0
pytest-xdist==3.3.1  # For parallel execution
```
Purpose: Specify exact library versions (reproducible environments)

---

### 🛠️ **Part 8: Debugging & Troubleshooting**

#### **Scenario 1: Test fails with "Connection refused"**
```
Problem: Database connection failed
Solution:
  1. Check config/config.py - correct server name?
  2. Check network connectivity: ping SERVER
  3. Check SQL Server is running
  4. Check credentials (Trusted_Connection=yes in Windows Auth)
```

#### **Scenario 2: Test passes but data not in database**
```
Problem: Test reports success but tables empty
Reason: Transaction was rolled back (isolation feature!)
Explanation:
  - Each test: BeginTransaction → Execute → Rollback
  - Database intentionally reset after each test
Solution:
  - This is by design! Tests don't pollute database
  - To verify data: Add assertions BEFORE rollback in test
```

#### **Scenario 3: Edit test skipped**
```
Problem: Edit_New_Schd_Team_01 doesn't run
Possible cause: Create_New_Schd_Team_01 failed
Solution:
  1. Run Create test alone: pytest tests/test_create_01.py::test_create_team[Create_New_Schd_Team_01]
  2. Check logs: output/tests/test_create_01.py/.../execution_gw0.log
  3. Fix the Create test first
  4. Edit will automatically run once Create succeeds
```

#### **Scenario 4: Need to enable/disable tests**
```
Solution: Edit keyword_driven_tests.csv
  - Find test row
  - Change Executed column: 'yes' → 'no' (disable) or 'no' → 'yes' (enable)
  - Save file
  - Re-run tests: pytest tests/ -v
```

---

### ✅ **Part 9: Best Practices**

1. **Keep test data independent**: Each Create test should work standalone
2. **Use meaningful test case IDs**: Create_LongText_06 clearly describes what it tests
3. **Write clear expected_result**: Help future developers understand intent
4. **Check logs after failures**: output/tests/.../execution_gw0.log has details
5. **Run tests frequently**: Before committing code changes
6. **Review HTML report**: Shows overall health of stored procedures
7. **Parallel execution**: Use `pytest -n auto` for speed (auto-detects CPU cores)
8. **Test database state**: Ensure pre-conditions are met before running tests

---

This section provides everything a new user needs to understand the framework!
                # ✅ Row 1: 'Create' == 'Create' ✓ and True ✓ → ADD 'Create_New_Schd_Team_01'
                # ✅ Row 2: 'Create' == 'Create' ✓ and True ✓ → ADD 'Create_Duplicate_Team_01'
                # ❌ Row 3: 'Create' == 'Create' ✓ but False ✗ → SKIP
                # ❌ Row 4: 'Edit' != 'Create' ✗ → SKIP
                
                test_cases.append(test_name)
    
    # Step 5h: Return filtered list
    return test_cases
    # Result: ['Create_New_Schd_Team_01', 'Create_Duplicate_Team_01']
```

---

### **Step 6: Back in [tests/test_create_01.py](tests/test_create_01.py#L12)**

```python
# Line 12: Filter out Duplicate tests
CREATE_TEST_CASES = [tc for tc in get_test_case_ids_by_operation('Create') if 'Duplicate' not in tc]

# Step 1: Call get_test_case_ids_by_operation('Create')
#         Output: ['Create_New_Schd_Team_01', 'Create_Duplicate_Team_01']

# Step 2: Filter with list comprehension [tc ... if 'Duplicate' not in tc]
#         'Create_New_Schd_Team_01': 'Duplicate' not in string? ✅ YES → KEEP
#         'Create_Duplicate_Team_01': 'Duplicate' not in string? ❌ NO → SKIP

# Final result: ['Create_New_Schd_Team_01']

# Step 3: pytest uses this list for parametrization
@pytest.mark.parametrize("test_case_id", CREATE_TEST_CASES, ids=CREATE_TEST_CASES)
# Runs test_create_team() once with test_case_id='Create_New_Schd_Team_01'
```

---

## Data Loading Architecture Diagram

```
pytest discovers test_create_01.py
    ↓
Line 12: CREATE_TEST_CASES = get_test_case_ids_by_operation('Create')
    ↓
[test_engine_layer/utils.py] get_test_case_ids_by_operation('Create')
    │
    ├─→ Call: load_test_data(None)
    │       ↓
    │   [test_engine_layer/utils.py] load_test_data(None)
    │       └─→ DataConfig.DEFAULT_TEST_DATA_FILE = 'keyword_driven_tests.csv'
    │           └─→ Call: TestDataLoader.load('keyword_driven_tests.csv')
    │
    ├─→ [data_loader_factory/factory.py] TestDataLoader.load()
    │   │   @staticmethod ← Pure function, no instance needed
    │   │   _LOADERS = {'.csv': CSVLoader, ...} ← Maps extension to loader
    │   │
    │   └─→ Auto-detect: ext = '.csv'
    │       └─→ loader_class = _LOADERS.get('.csv') = CSVLoader
    │           └─→ Call: CSVLoader.load('keyword_driven_tests.csv')
    │
    ├─→ [data_loader_factory/loaders/csv_loader.py] CSVLoader.load()
    │   │   @staticmethod ← Pure function
    │   │
    │   ├─ Build absolute path: C:\sp_validation\keyword_driven_tests.csv
    │   ├─ Open file with UTF-8 encoding
    │   ├─ Parse CSV with DictReader (uses headers as keys)
    │   ├─ Auto-detect schema: 'keyword-driven'
    │   ├─ Transform rows to standard format
    │   │   (Convert 'yes'/'no' strings to True/False booleans)
    │   │   (Parse JSON parameters strings to Python dicts)
    │   │
    │   └─→ Return: {
    │       'usp_CreateUpdateSchedulingTeam': [
    │           {'case_id': 'Create_New_Schd_Team_01', 'operation': 'Create', 'executed': True, ...},
    │           {'case_id': 'Create_Duplicate_Team_01', 'operation': 'Create', 'executed': True, ...},
    │           {'case_id': 'Create_New_Schd_Team_02', 'operation': 'Create', 'executed': False, ...},
    │           {'case_id': 'Update_Schd_Team_02', 'operation': 'Edit', 'executed': False, ...}
    │       ]
    │   }
    │
    └─→ Back in get_test_case_ids_by_operation()
        │
        └─ Filter: operation='Create' AND executed=True
            └─→ Result: ['Create_New_Schd_Team_01', 'Create_Duplicate_Team_01']
                │
                └─→ Back in test_create_01.py
                    └─ Filter: Remove if 'Duplicate' in test_case_id
                        └─→ Final: ['Create_New_Schd_Team_01']
                            └─→ pytest parametrizes test with this list
```

---

## Key Concepts: Data Loading Layer

| Concept | What It Is | Why It Matters | Example |
|---------|-----------|----------------|---------|
| **TestDataLoader** | Factory class with universal `load()` method | Single entry point for all formats (CSV/JSON/Excel) | `TestDataLoader.load('data.csv')` auto-detects format |
| **_LOADERS Dict** | Maps file extensions to loader classes | Enables format auto-detection without if/else chains | `_LOADERS['.csv']` = `CSVLoader` |
| **@staticmethod** | Method that doesn't need class instance | Enables pure functions inside classes | `TestDataLoader.load()` called directly on class |
| **BaseLoader** | Abstract base class (interface) | All loaders implement same contract | `JSONLoader`, `CSVLoader`, `ExcelLoader` all inherit |
| **Schema Auto-Detection** | Detects keyword-driven vs generic format | Eliminates need for config file to specify format | CSV reads headers automatically |
| **Type Conversion** | Transforms strings to proper types | Ensures consistent data types across all formats | `'yes'` string → `True` boolean |
| **Standardization** | Output always same dict structure | Downstream code doesn't care which format was loaded | All loaders return `{module: [rows]}` |

---

## File Reading Summary

```
┌─────────────────────────────────────────────────────────┐
│ DATA LOADING FLOW: From Disk to Python Dictionary      │
└─────────────────────────────────────────────────────────┘

CSV File (keyword_driven_tests.csv)
┌────────────────────────────────────────────────────────────┐
│ Module,Operation,Test Case ID,Executed,test_...,test_..   │
│ usp_Create...,Create,Create_New_Schd_Team_01,yes,...      │
│ usp_Create...,Create,Create_Duplicate_Team_01,yes,...     │
│ usp_Create...,Create,Create_New_Schd_Team_02,no,...       │
│ usp_Create...,Edit,Update_Schd_Team_02,no,...             │
└────────────────────────────────────────────────────────────┘
              ↓
         Opens as UTF-8 text file
         Reads with csv.DictReader
              ↓
     Detects column headers as keys
     Reads each row into dictionary
              ↓
     Auto-detects schema: 'keyword-driven'
     Transforms to standard format
              ↓
     Type Conversions:
     ✓ 'yes' → True
     ✓ 'no' → False
     ✓ JSON strings → Python dicts
     ✓ Headers → lowercase keys
              ↓
     Python Dictionary Structure
┌────────────────────────────────────────────────────────────┐
│ {                                                          │
│   'usp_CreateUpdateSchedulingTeam': [                      │
│     {                                                      │
│       'case_id': 'Create_New_Schd_Team_01',              │
│       'operation': 'Create',                              │
│       'module': 'usp_CreateUpdateSchedulingTeam',         │
│       'executed': True,  ← Converted from 'yes'          │
│       'description': '...',                               │
│       'parameters': {...}  ← Parsed from JSON string      │
│     },                                                     │
│     ...                                                    │
│   ]                                                        │
│ }                                                          │
└────────────────────────────────────────────────────────────┘
              ↓
     Filters by operation and executed flag
     Returns list of matching test case IDs
```

# View HTML report after running
# Open: reports/sp_automation_report.html
```

---

