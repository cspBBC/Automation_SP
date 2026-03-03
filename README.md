# SP Validation Framework

This repository is an automated testing framework for executing and validating stored-procedure (SP) workflows (Create → Edit flows and similar) against a SQL database in a safe, disposable transaction context. It is driven by keyword CSV input + JSON templates and includes utilities for executing SPs, chaining them, and validating results and history.

This README explains the purpose of the top-level files and each folder so any developer or tester can understand, run, and extend the framework.

---

## Quick Start

Prerequisites:
- Python 3.10+ virtual environment (this repo uses venv under `venv/` in examples)
- Database connectivity configured in `config/config.yaml` / `config/database.yaml`
- `requirements.txt` installed into the active environment

Typical commands:

- Install dependencies:

```bash
python -m pip install -r requirements.txt
```

- Run the small focused pytest suite:

```bash
python -m pytest -q
```

- Run a single test:

```bash
python -m pytest tests/test_edit_01.py::test_edit_updates_team_name_and_logs_history -q
```

- Run CSV-driven scaffold (standalone):

```bash
python run_csv_tests.py
```

This script runs Create + Edit flows discovered from `data_layer/test_data/keyword_driven_tests.csv` and logs comprehensive output to `output/csv_execution/execution.log`. It uses a transaction + savepoint to roll all changes back so the DB state is not modified.

---

## Top-level files

- `requirements.txt`: Python dependencies for the project.
- `pytest.ini`: pytest configuration for running tests.
- `run_csv_tests.py`: Standalone CSV-driven execution script (safe rollback using a transaction savepoint). Produces `output/csv_execution/execution.log`.
- `run_csv_tests.py` logs detailed scaffold execution and per-test summaries for manual runs.

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
    - `utils.py` - Logging setup, colors, and helpers used by the test runner.

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

To add a new SP module driven by CSV + templates:
1. Add or update a row in `data_layer/test_data/keyword_driven_tests.csv` for the module and operation.
2. Create a JSON template describing the operation(s) under `data_layer/test_data/modules/<ModuleName>/<ModuleName>_<Operation>.json`.
   - Templates may specify `chain_config` with step-level `parameters`, `input_mappings` and `output_mappings`.
3. Optionally add preseed SQL files to `data_layer/preseed_data/` and reference them in tests via `verify_preseed_exists()` so required reference rows exist.
4. Add/modify pytest tests in `tests/` which call `run_stored_procedures_from_csv()` or `run_stored_procedures()` (for single SP) and then call validators from `validation_layer/`.

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

