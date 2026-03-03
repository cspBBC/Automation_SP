# SP Validation Framework

This repository is an automated testing framework for executing and validating stored-procedure (SP) workflows (Create → Edit flows and similar) against a SQL database in a safe, disposable transaction context. It is driven by keyword CSV input + JSON templates and includes utilities for executing SPs, chaining them, and validating results and history.

This README explains the purpose of the top-level files and each folder so any developer or tester can understand, run, and extend the framework.

---

## Quick Start

Prerequisites:
- Python 3.10+ virtual environment (this repo uses venv under `venv/` in examples)
- Database connectivity configured in `config/config.yaml` / `config/database.yaml`
- `requirements.txt` installed into the active environment

### Installation

```bash
python -m pip install -r requirements.txt
```

### Running Tests

#### Option 1: Run all tests with pytest

```bash
python -m pytest tests/ -v
```

#### Option 2: Run individual test files

```bash
# Run Create test cases only
python -m pytest tests/test_create_01.py -v

# Run Edit test cases only
python -m pytest tests/test_edit_01.py -v
```

#### Option 3: Run specific test cases independently

Each test case in the CSV runs as an independent parametrized test:

```bash
# Run only one Create test case
python -m pytest tests/test_create_01.py::test_validate_created_team[Create_New_Schd_Team_04] -v

# Run only one Edit test case
python -m pytest tests/test_edit_01.py::test_edit_updates_team_successfully[Update_Schd_Team_01] -v
```

#### Option 4: Run CSV-driven scaffold (standalone)

```bash
python run_csv_tests.py
```

This script runs all test cases (Create + Edit flows) discovered from `data_layer/test_data/keyword_driven_tests.csv` where `Executed=Yes`. It uses a transaction + savepoint to roll all changes back so the DB state is not modified. Comprehensive logs are written to `output/csv_execution/execution.log`.

---

## Top-level files

- `requirements.txt`: Python dependencies for the project.
- `pytest.ini`: pytest configuration for running tests.
- `run_csv_tests.py`: Standalone CSV-driven execution script (safe rollback using a transaction savepoint). Produces `output/csv_execution/execution.log`. Run with: `python run_csv_tests.py`
- `__init__.py`, `conftest.py`: Package and pytest configuration files.

---

## Folder structure and purpose

Paths are workspace-relative. When a file is referenced, it appears as shown.

- `config/`
  - Purpose: configuration files for the framework (YAML + helper module).
  - Key files:
    - `config.py` - Python config utilities (loads YAML and provides configuration objects).
    - `config.yaml` - Primary configuration values (environment, logging defaults, paths, etc.).
    - `database.yaml` - Database connection configuration used by `database_layer/connection.py`.
    - `test_config.yaml` - Test-specific configuration overrides.

- `data_layer/`
  - Purpose: SQL fixtures, static test data, and CSV-driven test definitions.
  - Key subfolders/files:
    - `preseed_data/` - SQL files used to verify or seed required reference rows (e.g. `createSchdGroup_user.sql`, `createSchdGroup_division.sql`). These are executed by preseed validators to ensure tests have required reference data.
    - `test_data/` - Contains `keyword_driven_tests.csv` (the CSV that drives scaffold runs) and any JSON templates for stored-procedure inputs.

- `data_loader_factory/`
  - Purpose: Load test inputs from different formats (CSV, JSON, keyword-driven CSV).
  - Key files:
    - `factory.py` - Factory that picks the right loader for a given input type.

- `data_loader_factory/loaders/`
  - Purpose: concrete loaders for CSV / JSON / keyword-driven CSV formats.
  - Files:
    - `csv_loader.py`, `json_loader.py`, `keyword_driven_loader.py`, `base_loader.py`
  - The keyword-driven loader is used by `run_stored_procedures_from_csv()` to read the CSV and prepare modules and operations.

- `database_layer/`
  - Purpose: All direct database interaction: connection, transaction management, stored-procedure execution and chain executor for multi-step flows.
  - Key files:
    - `connection.py` - `DBSession` context manager and connection utilities.
    - `transaction_manager.py` - Utilities to set/get a test transaction so tests run against a savepoint/transaction that can be rolled back.
    - `procedure_executor.py` - Executes a stored procedure with parameter mapping and returns results.
    - `chain_executor.py` - `SPChainExecutor` which can execute a list of steps (chain) and extract outputs into `chain_data` for subsequent steps.
    - `normalizer.py` - Helpers to normalize SQL output rows into dicts.
    - `procedure_executor.py` - builds param type mappings and runs SPs.

- `test_engine_layer/`
  - Purpose: The test runner, template transformer, parameter manager, and supporting utils.
  - Key files:
    - `runner.py` - High-level APIs used by tests: `run_stored_procedures()` and `run_stored_procedures_from_csv()` implement the execution patterns (single SP or CSV scaffold). The scaffold auto-discovers modules, loads templates, executes chain-configs, and returns structured results including `execution_context`/`chain_data`.
    - `builder.py` - Constructs test contexts for parameter expansion.
    - `parameter_manager.py` - Utility to format and interpolate parameters into SP calls.
    - `template_transformer.py` - Loads JSON templates and uses CSV rows to create test cases.
    - `utils.py` - Logging setup, colors, and utility functions:
      - `get_test_case_ids_by_operation(operation)` - Load test case IDs from CSV filtered by operation type and execution status. Used in tests to parametrize fixtures.
      - `verify_preseed_for_module(module_name)` - Verify that all required preseed SQL files exist for a module. Module-aware preseed requirements are defined in `MODULE_PRESEED_FILES` dict.
      - `get_module_for_test_case(test_case_id)` - Look up the module name for a given test case ID from CSV.

- `loaders/` (already described in data_loader_factory)

- `validation_layer/`
  - Purpose: Collection of validators that query the DB to assert expected state after operations. Validators return boolean pass/fail and log detailed information to the test `execution.log` during test runs.
  - Key files:
    - `schGroup_validator.py` - Scheduling group (team) validators: `getSchdGrpDetails`, `getSchdGrpHistory`, `validateSchdGrpHistoryExists`, `validateSchdGrpHistoryAction`, `validateUserCanAccessTeam`, etc. These are used by tests to verify team creation/edit history and access controls.
    - `preseed_validator.py` - Ensures preseed SQL reference files exist and optionally executes them.
    - `generic_validators.py` - Reusable validators and helpers for executing queries and asserting generic conditions.

- `tests/`
  - Purpose: pytest tests and fixtures used to validate flows.
  - Key files:
    - `conftest.py` - pytest fixtures: `db_transaction` (sets a DB transaction and rolls it back), `output_dir` (per-test output directory), `setup_execution_logging` (adds `execution.log` per test), and captures for `stdout`/`stderr`. Important: `setup_execution_logging` attaches a `FileHandler` to the root logger so all module loggers write into `execution.log`.
    - `test_create_01.py` - Example test that runs `run_stored_procedures_from_csv()` to create a team and asserts properties.
    - `test_edit_01.py` - Minimal end-to-end test that runs Create→Edit flow via CSV, fetches details and history via validators, and asserts the edit history contains the expected entries.

- `output/`
  - Purpose: Destination for run-time artifacts and logs.
  - Key paths:
    - `output/csv_execution/execution.log` - log file for `run_csv_tests.py` standalone runs.
    - `output/tests/<test_nodeid>/<test_name>/execution.log` - per-test `execution.log` generated by pytest fixture. `stdout.txt` and `stderr.txt` are also stored here by the capture fixture.

---

## How the CSV -> Template -> Chain flow works (high level)

1. `run_stored_procedures_from_csv()` (in `test_engine_layer/runner.py`) reads `data_layer/test_data/keyword_driven_tests.csv` using the keyword-driven loader.
2. It extracts unique module names and requested operations (Create, Edit, etc.).
3. For each operation it finds an operation-specific JSON template (in `data_layer/test_data/modules/<module>/` or `data_layer/test_data/`). Templates define `chain_config` steps, parameter mappings and output mappings.
4. For each test case the runner constructs a parameter context, optionally executes pre-SQL, then runs either a single SP or a chain using `SPChainExecutor`.
5. `SPChainExecutor` runs each step, logs the SP outputs, and extracts mapped values into `chain_data` (e.g. `created_team_id`). That `chain_data` is used to inject inputs to later steps in the chain (Edit uses the ID from Create).
6. After execution, the runner returns structured results with `execution_context` / `chain_data` and `status` fields per case that tests or the standalone script can inspect.

---

## Logging and capturing results

- `pytest` runs attach a `FileHandler` to the root logger (via `tests/conftest.py::setup_execution_logging`) which writes all logger output to the per-test `execution.log`. This gives a complete step-by-step transcript for debugging.
- The standalone script `run_csv_tests.py` also writes `output/csv_execution/execution.log` and prints a concise results summary to console. It uses a DB savepoint so the run can be rolled back.
- Validators in `validation_layer/` use logging to explain queries executed, result counts, and key fields — making it easy to compare expectations with DB state.

---

## Adding new tests or modules

### Adding a new test case to existing module

1. Add a new row to `data_layer/test_data/keyword_driven_tests.csv` with `Executed=Yes`:
   ```
   usp_CreateUpdateSchedulingTeam,Create,Create_New_Schd_Team_05,Yes,"Description",...test parameters...
   ```
2. **No test code changes needed!** Existing pytest tests automatically discover and parametrize the new test case.
3. Run tests:
   ```bash
   python -m pytest tests/test_create_01.py -v
   ```
   The new test case will appear and run independently from other test cases.

### Adding a new SP module with its own operation(s)

1. **Add preseed file mapping** in `test_engine_layer/utils.py`:
   ```python
   MODULE_PRESEED_FILES = {
       'usp_CreateUpdateSchedulingTeam': ['createSchdGroup_user.sql', 'createSchdGroup_division.sql'],
       'usp_ModuleTwo': ['preseed_module_two_users.sql', 'preseed_module_two_configs.sql'],  # ← New
   }
   ```

2. **Create preseed SQL files** in `data_layer/preseed_data/`:
   ```
   preseed_module_two_users.sql
   preseed_module_two_configs.sql
   ```

3. **Add rows to CSV** `data_layer/test_data/keyword_driven_tests.csv`:
   ```
   usp_ModuleTwo,Create,Create_Resource_01,Yes,"Description",...parameters...
   usp_ModuleTwo,Edit,Edit_Resource_01,Yes,"Description",...parameters...
   ```

4. **Create JSON templates** in `data_layer/test_data/modules/usp_ModuleTwo/`:
   ```
   usp_ModuleTwo_Create.json
   usp_ModuleTwo_Edit.json
   ```
   Templates define `chain_config` steps with parameter and output mappings.

5. **Create test file** `tests/test_usp_module_two.py` (optional, or extend existing):
   ```python
   from test_engine_layer.utils import get_test_case_ids_by_operation, verify_preseed_for_module, get_module_for_test_case
   
   CREATE_TEST_CASES = get_test_case_ids_by_operation('Create')
   
   @pytest.fixture
   def created_resource_id(db_transaction, request):
       test_case_name = request.param
       module_name = get_module_for_test_case(test_case_name)
       verify_preseed_for_module(module_name)
       result = run_stored_procedures_from_csv(filter_test_name=test_case_name)
       # Extract and return resource ID
   
   @pytest.mark.parametrize("created_resource_id", CREATE_TEST_CASES, indirect=True, ids=CREATE_TEST_CASES)
   def test_validate_created_resource(created_resource_id):
       # Validation logic
   ```

6. **Run tests** - they automatically discover and run all test cases:
   ```bash
   python -m pytest tests/test_usp_module_two.py -v
   ```

---

## Independent Test Execution

Tests use **pytest parametrization** with indirect fixtures to ensure each CSV test case:
- Runs in **isolated database context** (per-test transaction rolled back)
- Does **not depend** on other test cases
- Can be **added to CSV without code changes**
- Can be **run individually** by name

Example: Run one Create test in isolation:
```bash
python -m pytest tests/test_create_01.py::test_validate_created_team[Create_New_Schd_Team_04] -v
```

---

## Module-Aware Preseed Verification

Preseed requirements vary by module. The framework handles this automatically:
1. **Preseed mapping** defined in `test_engine_layer/utils.py::MODULE_PRESEED_FILES`
2. **Preseed verification** happens per-module when test fixtures run
3. **Scalable:** Add new modules by extending `MODULE_PRESEED_FILES` with appropriate SQL files

When you add a new module, just:
1. Update the preseed mapping
2. Create SQL files in `data_layer/preseed_data/`
3. Add CSV rows - tests use the mapping automatically

---

## Developer notes & conventions

- Status fields returned by the runner are canonical uppercase strings: `PASSED`, `FAILED`, `SKIPPED`.
- `execution_context` / `chain_data` is a standard dictionary used to pass outputs from Create steps to subsequent steps.
- Database interactions should use the `DBSession` context manager where possible to ensure cursors and connections are managed.
- Tests run under a `db_transaction` fixture (see `tests/conftest.py`) to isolate DB changes and roll them back after each test.
- When editing logging behavior, prefer using the existing root handler approach so logs are captured in `execution.log`. Avoid closing handlers early (teardown should remove and close handlers after test finishes).

---

## Troubleshooting

- If `execution.log` shows `ValueError: I/O operation on closed file`, it indicates a log handler was closed while other modules were still emitting logs. Ensure handlers are removed after test teardown and that no background threads are still logging.
- If the CSV runner prints `⏭️  SKIPPED` for a case showing as `PASSED` in the runner output, check the `status` capitalization and the script that prints case results — the framework expects uppercase statuses but `run_csv_tests.py` is robust to case mismatches.

---

## Where to look next

- Test flow: `test_engine_layer/runner.py`
- Chain execution internals: `database_layer/chain_executor.py`
- Stored-procedure execution and param mapping: `database_layer/procedure_executor.py`
- Templates and CSV transformation: `test_engine_layer/template_transformer.py`
- Validators for scheduling teams: `validation_layer/schGroup_validator.py`
- Pytest fixtures and per-test logging: `tests/conftest.py`

---

If you want, I can also:
- Generate a smaller `DEVELOPER.md` with step-by-step instructions for adding a new SP module and template.
- Create example templates or demonstrate adding a new CSV row and template.

---

## Session Summary (2026-03-03)

This project has been significantly enhanced during a recent development session. Key outcomes and architectural improvements are captured here for developer context:

### Architecture Enhancements

- **Independent Test Execution:** Refactored test fixtures to use pytest parametrization with indirect fixtures. Each CSV test case now runs in a completely isolated database transaction context with no dependencies on other test cases. Tests can be added to CSV without code modifications and run individually by name.

- **Centralized Test Case Discovery:** Created `get_test_case_ids_by_operation(operation)` utility in `test_engine_layer/utils.py` to eliminate code duplication across test files. This single function loads test case IDs filtered by operation type and execution status, supporting unlimited test cases and operations.

- **Module-Aware Preseed Verification:** Implemented a scalable preseed verification system:
  - `MODULE_PRESEED_FILES` dictionary in `utils.py` maps module names to required preseed SQL files
  - `verify_preseed_for_module(module_name)` automatically checks if required files exist
  - `get_module_for_test_case(test_case_id)` looks up module from CSV
  - **Zero code changes needed when adding new modules** — just extend the mapping and create SQL files

- **Code Optimization:** Both `test_create_01.py` and `test_edit_01.py` were refactored for clarity and efficiency:
  - Reduced fixture code by ~50% through removal of defensive duplication
  - Simplified result extraction from runner outputs
  - Removed unnecessary variable tracking in return values
  - All changes maintain 100% backward compatibility

### Previous Session Notes (Earlier 2026-03-03)

- **Focused test created:** A minimal `tests/test_edit_01.py` flow runs Create → Edit and validates the Edit and history entries.
- **Validator logging:** Validators in `validation_layer/` were iterated from `print()` to Python `logging` calls so output appears in per-test `execution.log`. A transient race (`I/O operation on closed file`) was diagnosed and addressed during the session.
- **Logging race resolved:** Multiple mitigations were tried (queue-based logging, a print-based lightweight logger, and careful fixture teardown). Current README still recommends attaching a root handler per test and avoiding premature handler closure.
- **History normalization:** `getSchdGrpHistory` was enhanced to add an `operation` key (heuristic: parse `History` text then fallback to `HistoryType`/`HistorySubType`) so tests can reliably filter history rows by operation (e.g. `edit`).
- **Fixture robustness:** `tests/test_create_01.py` fixture `created_team_id` was made resilient to several possible runner result shapes so downstream Edit steps reliably receive the created ID.
- **CSV runner fix:** `run_csv_tests.py` was patched to handle `status` case-insensitively; this fixed incorrect `⏭️  SKIPPED` outputs when the runner emitted uppercase statuses (`PASSED`/`FAILED`).
- **Test results:** After fixes, focused and full pytest runs reported passing tests (final observed: 2 passed, 0 failed, 0 skipped) and the standalone CSV runner showed both cases as PASSED.

### Test Results

Current test status (all passing):
```bash
tests/test_create_01.py::test_validate_created_team[Create_New_Schd_Team_04] PASSED
tests/test_edit_01.py::test_edit_updates_team_successfully[Update_Schd_Team_01] PASSED
============================== 2 passed ==============================
```

All independent test cases execute successfully with zero cross-test dependencies.

### Framework Scalability

The framework now supports:
- **Unlimited test cases** - add to CSV, tests parametrize automatically
- **Multiple modules** - extend preseed mapping, no code changes to test logic
- **Multiple operations** - Create, Edit, Delete, etc. use same pattern
- **Independent execution** - each test case runs in isolated transaction context
- **Easy debugging** - run individual test cases by name without affecting others

