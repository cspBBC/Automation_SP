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

