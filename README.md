# Testing Framework - Complete E2E Documentation

This directory contains a comprehensive test harness for validating SQL stored procedures (SPs). This document explains every piece of the framework, how they work together, and walks through a real example line-by-line.

---

## 📋 Table of Contents

1. [Framework Architecture](#framework-architecture)
2. [Directory Structure](#directory-structure)
3. [Core Components Explained](#core-components-explained)
4. [E2E Workflow with Example](#e2e-workflow-with-example)
5. [Data Structures & Return Types](#data-structures--return-types)
6. [Usage Guide](#usage-guide)

---

## Framework Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TEST RUNNER                              │
│         (NP036_SP_run.py or any user script)                │
│  test_stored_procedures('usp_Name', TestCaseType, filename) │
└────┬────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│              LOAD TEST INPUTS (sp_test_utils.py)            │
│  load_test_inputs(filename) → Returns Dict from JSON file   │
└────┬────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│              FILTER TEST CASES (sp_test_utils.py)           │
│  • Find SP name in loaded dict                              │
│  • Filter by case_type (POSITIVE/NEGATIVE/EDGE)            │
│  • Extract matching test cases array                        │
└────┬────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│            DETECT & EXECUTE TEST (sp_test_utils.py)         │
│  • Single execution: run_stored_procedure()                │
│  • Chained execution: SPChainExecutor.execute_chain()      │
│  • Print results & errors                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
tests/
├── __init__.py                          # Package marker
├── NP036_SP_run.py                      # EXAMPLE: Test runner script
├── test_data/
│   ├── test_inputs.json                 # DEFAULT: Test cases JSON
│   └── test_inputs1.json                # CUSTOM: Alternative test cases JSON
├── enums/
│   ├── __init__.py                      # Package marker
│   └── test_enums.py                    # Defines TestCaseType enum
├── helpers/
│   ├── __init__.py                      # Package marker
│   └── sp_test_utils.py                 # CORE: Main testing utilities
└── __pycache__/                         # Python bytecode cache
```

---

## Core Components Explained

### 1. **test_enums.py** - Test Case Type Definitions

**Purpose:** Define categories of test cases to organize and filter tests.

**What it contains:**
```python
from enum import Enum

class TestCaseType(Enum):
    POSITIVE = "POSITIVE"      # Tests that should succeed normally
    NEGATIVE = "NEGATIVE"      # Tests that should fail gracefully  
    EDGE = "EDGE"              # Boundary/edge case tests
```

**Why it exists:**
- Provides a standardized way to categorize tests
- Prevents typos (using enum instead of strings)
- Makes it easy to run only certain test types (e.g., all POSITIVE tests)
- Improves code clarity and maintainability

**Meaning of each type:**
- **POSITIVE**: Expected happy-path scenarios. SP should execute successfully and return valid results
- **NEGATIVE**: Invalid inputs or error conditions. SP should handle gracefully with error messages
- **EDGE**: Boundary values, extreme cases (MAX int, empty strings, NULL values, etc.)

---

### 2. **test_inputs.json / test_inputs1.json** - Test Case Data

**Purpose:** Define what parameters to pass to each stored procedure and what to expect.

**Structure (JSON format):**
```json
{
  "usp_CreateUpdateSchedulingTeam": [
    {
      "case_id": "POSITIVE_CHAIN_CREATE_UPDATE_VALIDATE",
      "case_type": "POSITIVE",
      "description": "3-step chain: Create team, update allocations, update miscellaneous",
      "chain_config": [
        {
          "step": 1,
          "sp_name": "usp_CreateUpdateSchedulingTeam",
          "parameters": {
            "@schedulingTeamName": "AutoTest_20260227_181957_457",
            "@divisionId": 6,
            ...
          },
          "output_mapping": {
            "@intnewteamid": "created_team_id"
          }
        },
        {
          "step": 2,
          "sp_name": "usp_UpdateAllocation",
          ...
        }
      ]
    },
    {
      "case_id": "POSITIVE_SINGLE",
      "case_type": "POSITIVE",
      "description": "Simple single SP execution",
      "parameters": {
        "@schedulingTeamName": "Team1",
        "@divisionId": 1,
        ...
      }
    }
  ]
}
```

**Field Meanings:**
- **Top-level keys** (e.g., `"usp_CreateUpdateSchedulingTeam"`): Stored procedure names that become the test groups
- **Array of test cases**: Each SP can have multiple test cases of different types
- **case_id**: Unique identifier for this specific test case (e.g., "POSITIVE_CHAIN_CREATE_UPDATE_VALIDATE")
- **case_type**: Must match enum (POSITIVE, NEGATIVE, or EDGE) - used to filter tests
- **description**: Human-readable explanation of what this test validates
- **parameters**: Named parameters (@param_name) to pass to SP (used for single execution)
- **chain_config**: Array of sequential SP steps (used for chained execution). Each step:
  - **step**: Numeric order (1, 2, 3...)
  - **sp_name**: Which SP to call in this step
  - **parameters**: Parameters for this SP (can reference outputs from previous steps)
  - **output_mapping**: Maps SP output parameters to chain variables (key = SP param, value = chain variable name)

**Why this structure:**
- All test data in one file, no code changes needed to add tests
- Supports both single and chained SP executions
- Named parameters make large parameter lists readable
- Output mapping allows passing results between chained SPs

---

### 3. **sp_test_utils.py** - Core Testing Engine

**Purpose:** Load test data, execute SPs, and report results.

#### **Function 1: load_test_inputs(test_inputs)**

```python
def load_test_inputs(test_inputs):
    """Load test inputs from JSON file in tests/test_data folder.
    
    Args:
        test_inputs: Filename without extension (e.g., 'users_tests', 'shekjar', 'schgrp_fta').
                    MANDATORY - must be provided.
                    Function automatically appends .json extension.
    """
```

**What it does:**
1. Takes a filename (e.g., `"test_inputs1"`)
2. Constructs full path: `tests/test_data/test_inputs1.json`
3. Reads and parses the JSON file
4. Returns it as a Python dictionary

**Return type:** `dict`

**Example:**
```python
result = load_test_inputs('test_inputs1')
# Returns:
# {
#   "usp_CreateUpdateSchedulingTeam": [
#     {"case_id": "...", "case_type": "...", ...},
#     {...}
#   ],
#   "usp_GetUsers": [...]
# }
```

**Why it exists:**
- Centralizes JSON loading logic
- Makes filenames flexible (no hardcoding paths)
- Automatically appends `.json` extension (convenience)
- Handles file not found errors gracefully

---

#### **Function 2: test_stored_procedures(sp_name, case_type, test_inputs)**

```python
def test_stored_procedures(sp_name, case_type=None, test_inputs=None):
    """
    Run test cases from JSON matching the given stored procedure name.
    
    Args:
        sp_name: Name of the stored procedure (e.g., 'usp_CreateUpdateSchedulingTeam')
        case_type: TestCaseType enum member (POSITIVE, NEGATIVE, EDGE) or string
        test_inputs: Filename without extension (e.g., 'users_tests', 'shekjar', 'schgrp_fta').
                    MANDATORY - must be provided.
    """
```

**What it does (step-by-step):**

1. **Load JSON:** `test_data = load_test_inputs(test_inputs)`
   - Calls load_test_inputs to get the full test data dictionary

2. **Find SP tests:** Check if `sp_name` exists in `test_data`
   - If not found, print error message and return

3. **Extract test cases:** `test_cases = test_data[sp_name]`
   - Gets array of all test cases for this SP
   - Example: `test_data['usp_CreateUpdateSchedulingTeam']` returns the array of test cases

4. **Filter by type:** If case_type provided, filter test_cases
   - Keeps only test cases where `case_type` matches (POSITIVE, NEGATIVE, EDGE)
   - Converts enum `.name` to uppercase for comparison

5. **Iterate and execute:** For each test case:
   - Extract metadata (case_id, description, etc.)
   - Print separator and test info
   - Detect execution type:
     - **If has 'chain_config'**: Call `_execute_chain_test()`
     - **If has 'parameters'**: Call `_execute_single_test()`
   - Print results or errors

**Return type:** `None` (prints to console, raises exceptions on error)

**Example flow:**
```python
test_stored_procedures('usp_CreateUpdateSchedulingTeam', TestCaseType.POSITIVE, 'test_inputs1')
# Step 1: Load test_inputs1.json
# Step 2: Find 'usp_CreateUpdateSchedulingTeam' in loaded dict ✓ Found
# Step 3: Get all test cases for this SP (array)
# Step 4: Filter to only POSITIVE type test cases
# Step 5: For each POSITIVE case:
#   - Print case info
#   - Detect if single or chain execution
#   - Execute and print results
```

---

#### **Function 3: _execute_single_test(sp_name, parameters)**

```python
def _execute_single_test(sp_name, parameters):
    """Execute a single SP test."""
```

**What it does:**
1. Calls `run_stored_procedure(sp_name, parameters)` from core.db.procedures
2. Receives result (list of rows or None)
3. Prints results in formatted output

**Return type:** `None` (prints output)

**What run_stored_procedure returns:** 
- List of database rows (tuples or named tuples) if SP has SELECT statements
- Empty list if no results
- None if SP has no output

---

#### **Function 4: _execute_chain_test(chain_config)**

```python
def _execute_chain_test(chain_config):
    """Execute a chained SP test."""
```

**What it does:**
1. Gets database connection
2. Creates SPChainExecutor instance
3. Calls `executor.execute_chain(chain_config)`
4. Prints success or failure with details

**chain_config structure:**
```python
chain_config = [
  {
    "step": 1,
    "sp_name": "usp_Create",
    "parameters": {...},
    "output_mapping": {"@outParam": "chain_var_name"}
  },
  {
    "step": 2,
    "sp_name": "usp_Update",
    "parameters": {...}  # Can reference chain variables from step 1
  }
]
```

**SPChainExecutor.execute_chain() return type:** `dict`
```python
{
  'success': True/False,           # Whether ALL steps succeeded
  'failed_step': 1,                # Which step failed (if any)
  'error': 'Error message',        # Error description
  'chain_data': {                  # Data passed between steps
    'created_team_id': 123,
    'team_name': 'AutoTest_...'
  },
  'partial_results': {             # Results from steps before failure
    'step_1': {'rows': [...]},
    'step_2': {'rows': [...]}
  }
}
```

**Why this exists:**
- Real-world testing often needs multiple related SP calls in sequence
- Step 1 creates data, Step 2 updates it, Step 3 validates it
- Need to capture outputs from earlier steps and pass to later steps
- Need to track which step failed if there's an error

---

## E2E Workflow with Example

### **Real Example: NP036_SP_run.py**

```python
from tests.helpers.sp_test_utils import test_stored_procedures
from tests.enums.test_enums import TestCaseType

test_stored_procedures('usp_CreateUpdateSchedulingTeam', TestCaseType.POSITIVE, "test_inputs1")
```

### **Line-by-Line Execution:**

**Line 1-2: Imports**
```python
from tests.helpers.sp_test_utils import test_stored_procedures
```
- Imports the main test function from sp_test_utils.py
- This function coordinates the entire testing workflow

```python
from tests.enums.test_enums import TestCaseType
```
- Imports the enum with test case type definitions (POSITIVE, NEGATIVE, EDGE)
- Ensures type-safe filtering

**Line 4: Execute**
```python
test_stored_procedures('usp_CreateUpdateSchedulingTeam', TestCaseType.POSITIVE, "test_inputs1")
```

### **What Happens Inside:**

#### **Step 1: Load Test Data**
```python
test_data = load_test_inputs("test_inputs1")  # Load tests/test_data/test_inputs1.json
```
- File is parsed into Python dictionary:
```python
{
  "usp_CreateUpdateSchedulingTeam": [
    {
      "case_id": "POSITIVE_CHAIN_CREATE_UPDATE_VALIDATE",
      "case_type": "POSITIVE",
      "description": "3-step chain: Create team, update allocations...",
      "chain_config": [...]
    }
  ]
}
```

#### **Step 2: Verify SP Exists in Test Data**
```python
sp_name = 'usp_CreateUpdateSchedulingTeam'
if sp_name not in test_data:  # Check if this SP has test cases
    print("No test cases found...")
    return
# ✓ FOUND - proceed
```

#### **Step 3: Extract Test Cases for This SP**
```python
test_cases = test_data['usp_CreateUpdateSchedulingTeam']
# Result: Array with 1 test case object
# [
#   {
#     "case_id": "POSITIVE_CHAIN_CREATE_UPDATE_VALIDATE",
#     "case_type": "POSITIVE",
#     "chain_config": [...]
#   }
# ]
```

#### **Step 4: Filter by Case Type**
```python
case_type = TestCaseType.POSITIVE  # Enum member
normalized = case_type.name.upper()  # Convert to "POSITIVE"

# Filter: keep only cases where case_type == "POSITIVE"
test_cases = [tc for tc in test_cases 
             if tc.get('case_type', '').upper() == normalized]
# Result: Keeps the 1 POSITIVE test case (same as before in this example)
```

#### **Step 5: Iterate and Execute**
```python
for idx, test_case in enumerate(test_cases, 1):
    # idx=1, test_case = {"case_id": "...", "case_type": "POSITIVE", ...}
    
    case_id = test_case.get('case_id', f'case_{idx}')  # "POSITIVE_CHAIN_CREATE_UPDATE_VALIDATE"
    case_type_label = test_case.get('case_type', 'unknown')  # "POSITIVE"
    description = test_case.get('description', '')  # "3-step chain: ..."
    
    # Print header
    print("\n" + "="*80)
    print(f"[1/1] Case: POSITIVE_CHAIN_CREATE_UPDATE_VALIDATE")
    print(f"Type: POSITIVE")
    print(f"Description: 3-step chain: Create team, update allocations...")
    print("="*80)
    
    # Detect execution type
    if 'chain_config' in test_case:  # ✓ This test case HAS chain_config
        _execute_chain_test(test_case['chain_config'])
        # Calls SPChainExecutor to run 3 sequential SPs
    else:
        _execute_single_test(sp_name, test_case['parameters'])
```

#### **Step 6: Chain Execution Details**

Inside `_execute_chain_test(chain_config)`:
```python
# chain_config is array of 3 steps
connection = get_connection()  # Get DB connection
executor = SPChainExecutor(connection)
result = executor.execute_chain(chain_config)

# Returns:
# {
#   'success': True/False,
#   'failed_step': None,
#   'error': None,
#   'chain_data': {
#     'created_team_id': 12345,    # Output from step 1
#     'updated_count': 5           # Output from step 2
#   },
#   'partial_results': {...}
# }
```

#### **Step 7: Print Results**
```python
if result['success']:
    print("\n[SUCCESS] Chain execution completed successfully!")
    print("\nChain data (extracted/passed between steps):")
    print(f"  created_team_id: 12345")
    print(f"  updated_count: 5")
else:
    print("\n[FAILED] CHAIN EXECUTION FAILED")
    print(f"Failed at: STEP {result['failed_step']}")
    print(f"Error: {result['error']}")
    # Print partial results up to failure point
```

---

## Data Structures & Return Types

### **load_test_inputs() Return Type: `dict`**

```python
{
  "usp_CreateUpdateSchedulingTeam": [
    {"case_id": "...", "case_type": "...", ...},
    {...}
  ],
  "usp_GetUsers": [
    {...}
  ]
}
```

### **test_stored_procedures() Return Type: `None`**

- Prints all output to console
- Raises `FileNotFoundError` if JSON file not found
- Raises `ValueError` if test_inputs not provided (mandatory)

### **run_stored_procedure() Return Type: `list` or `None`**

```python
# From core.db.procedures
result = run_stored_procedure('usp_GetUsers', {'@userId': 123})

# Returns:
# [
#   Row(id=1, name='User1', email='user1@example.com'),
#   Row(id=2, name='User2', email='user2@example.com')
# ]
# OR: None if no results
```

### **SPChainExecutor.execute_chain() Return Type: `dict`**

```python
{
  'success': bool,
  'failed_step': int | None,
  'error': str | None,
  'chain_data': dict,           # Variables passed between steps
  'partial_results': dict       # Results from completed steps
}
```

---

## Usage Guide

### **Basic Usage: Run Tests**

```python
from tests.helpers.sp_test_utils import test_stored_procedures
from tests.enums.test_enums import TestCaseType

# Run only POSITIVE tests for usp_CreateUpdateSchedulingTeam from test_inputs1.json
test_stored_procedures('usp_CreateUpdateSchedulingTeam', TestCaseType.POSITIVE, "test_inputs1")

# Run only NEGATIVE tests
test_stored_procedures('usp_GetUsers', TestCaseType.NEGATIVE, "test_inputs1")

# Run only EDGE case tests
test_stored_procedures('usp_ValidateTeam', TestCaseType.EDGE, "test_inputs1")
```

### **Create New Test File**

1. Create JSON file in `tests/test_data/` directory (e.g., `my_tests.json`)

2. Define test structure:
```json
{
  "usp_YourProcedure": [
    {
      "case_id": "POSITIVE_CASE_1",
      "case_type": "POSITIVE",
      "description": "What this test validates",
      "parameters": {
        "@param1": "value1",
        "@param2": 123
      }
    },
    {
      "case_id": "NEGATIVE_INVALID_INPUT",
      "case_type": "NEGATIVE",
      "description": "Test with invalid input",
      "parameters": {
        "@param1": "invalid",
        "@param2": -999
      }
    }
  ]
}
```

3. Use in tests:
```python
test_stored_procedures('usp_YourProcedure', TestCaseType.POSITIVE, "my_tests")
```

### **Add Chained Tests**

```json
{
  "usp_CreateUpdateSchedulingTeam": [
    {
      "case_id": "CHAIN_CREATE_THEN_UPDATE",
      "case_type": "POSITIVE",
      "description": "Create team, then update it",
      "chain_config": [
        {
          "step": 1,
          "sp_name": "usp_CreateTeam",
          "parameters": {
            "@teamName": "TestTeam",
            "@divisionId": 1
          },
          "output_mapping": {
            "@outTeamId": "team_id"
          }
        },
        {
          "step": 2,
          "sp_name": "usp_UpdateTeam",
          "parameters": {
            "@teamId": "$(team_id)",
            "@newName": "UpdatedTeam"
          }
        }
      ]
    }
  ]
}
```

### **Generate Skeletal Parameters**

For SPs with many parameters, auto-generate parameter template:

```bash
python -m contrib.generate_params usp_CreateUpdateSchedulingTeam --named
```

Output:
```python
{
  "@schedulingTeamName": "",
  "@schedulingTeamDescription": "",
  "@divisionId": 0,
  "@isActive": 0,
  ...
}
```

Copy this into your JSON test file and fill in values.

---

## Key Concepts Summary

| Concept | Purpose | Type |
|---------|---------|------|
| **TestCaseType Enum** | Categorize tests (POSITIVE/NEGATIVE/EDGE) | Classification |
| **JSON Test File** | Define test data and expected behavior | Data |
| **load_test_inputs()** | Parse JSON into Python dict | Loader |
| **test_stored_procedures()** | Main orchestrator function | Controller |
| **_execute_single_test()** | Run one SP once | Executor |
| **_execute_chain_test()** | Run multiple SPs sequentially | Executor |
| **SPChainExecutor** | Manages chained SP execution | Engine |
| **chain_data** | Variables passed between chain steps | State |
| **output_mapping** | Map SP outputs to chain variables | Transformer |

---

## Why Each Piece Exists

| Component | Why Created | Benefit |
|-----------|-------------|---------|
| Enum | Type safety, prevent typos | Can't use invalid case types by accident |
| JSON files | Separate data from code | Add tests without recompiling code |
| load_test_inputs() | Centralize loading logic | Flexible filenames, consistent error handling |
| test_stored_procedures() | Main orchestration | One function call runs entire test workflow |
| Single test function | Basic execution | Simplest case is straightforward |
| Chain test function | Complex workflows | Real-world scenarios need multiple SPs |
| SPChainExecutor | State management | Track data passed between steps |
| output_mapping | Variable capture | Step 2 can use outputs from Step 1 |

---

## Adding New Helpers

Place reusable helpers in `tests/helpers/` and scripts/one-off utilities in `contrib/`.

**Example:** If you create `tests/helpers/my_helper.py`:
```python
def my_helper_function():
    """Useful utility"""
    pass
```

Import it in tests:
```python
from tests.helpers.my_helper import my_helper_function
```
