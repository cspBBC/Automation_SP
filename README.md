# SP Validation Framework

## Overview

This repository contains a validation framework for stored procedures (SPs) in a
Microsoft SQL Server database. Its goal is to provide automated tests and utility
functions that make it easy to verify the structure, parameters and behaviour of
stored procedures. New team members can run tests locally, add new SP checks, and
use shared helpers to simplify database interactions.

---

## Why this framework exists ✅

- **Consistency**: Stored procedures across projects must follow naming,
  parameter and data-type conventions. Manual reviews are error-prone.
- **Regression protection**: A change in a SP can unintentionally break
  downstream code. The test suite quickly highlights failures.
- **Onboarding**: New developers can understand SPs and related helpers without
  deep database knowledge.
- **Reusable tools**: Common logic for parameter normalization, connection
  management and result validation is centralized.

---

## What is included 📁

The workspace is organized as follows:

```
├── config/             # environment and database configuration
├── core/               # core modules used by tests and utilities
│   └── db/             # database helpers and normalization logic
├── contrib/            # optional scripts, helpers, and documentation
├── tests/              # pytest-based test definitions and helpers
└── README.md           # (this file) overview and instructions
```

### Key directories and files

| Path                                  | Purpose
|---------------------------------------|--------------------------------------------------
| `config/config.py`                    | Loads environment `.env` and validates DB
| `core/db/connection.py`              | `DBSession` context manager wrapping pyodbc or similar
| `core/db/procedures.py`              | SP parameter introspection & executor
| `core/db/sql_normalizer.py`          | Formats Python values per SQL type
| `core/db/sp_chain_executor.py`       | (used by contrib) executes chains of SPs
| `tests/conftest.py`                  | pytest fixtures (e.g. `db_session`) and shared config
| `tests/helpers/`                      | small helpers used by tests (query generation, pre-seeding)
| `tests/modules/*.py`                 | module-specific SP tests (`test_create_01.py`, `test_edit_01.py`)
| `contrib/`                            | ad-hoc scripts for database inspection, permission checks, etc.

Additional documentation files in `contrib/` explain architecture and
migration guides; they serve as reference rather than executable code.

---

## How to get started 🔧

1. **Clone the repo**:
   ```bash
   git clone https://github.com/yourorg/sp_validation.git
   cd sp_validation
   ```

2. **Create a Python virtual environment** (Windows example):
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Configure database connection**
   - Copy `.env.example` (if provided) to `.env` or export environment
     variables manually.
   - Required variables: `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
   - Optionally set `DB_DRIVER` if not using the default SQL Server driver.

4. **Run the test suite**:
   ```bash
   pytest -q
   ```
   - Tests under `tests/modules` use helper classes to validate specific
     stored procedures. See each test file for configurable parameters.

5. **Adding a new stored procedure test**
   - Create a file under `tests/modules` named `test_<sp_name>.py`.
   - Use existing tests as templates, import helpers from
     `tests/helpers/sp_test_utils.py` and `core/db/procedures.py`.
   - Optionally add new validators in `tests/modules/**_validator.py`.

6. **Using core helpers directly in scripts**
   - Import `DBSession` from `core.db.connection` to run queries.
   - Call `procedures.run_stored_procedure` with a dict to automatically
     normalize parameters.

---

## File-by-file explanation

- **`requirements.txt`**: Python dependencies. Key packages include
  `pytest`, `python-dotenv` and whatever database driver is used (`pyodbc`,
  `pymssql`, `sqlalchemy`, etc.).

- **`pytest.ini`**: pytest configuration for test discovery and markers.

- **`config/config.py`**: Loads `.env` and defines a `DatabaseConfig` class with a
  `validate()` method. Use `DatabaseConfig.validate()` early in any script to
  ensure environment variables are set.

- **`core/db/connection.py`**: A simple wrapper providing a `DBSession` context
  manager. It reads connection settings from `DatabaseConfig` and uses them to
  open a cursor. The context manager automatically commits/rolls back and
  cleans up resources.

- **`core/db/sql_normalizer.py`**: Contains logic for converting Python values
  (strings, dates, booleans) into formats appropriate for SQL Server parameter
  binding. It also defines `SQLDataType` constants used throughout the framework.

- **`core/db/procedures.py`**: The heart of SP interaction. Features include
  looking up parameter metadata (`get_stored_procedure_parameters`), building
  type mappings, and executing SPs with normalization via
  `run_stored_procedure`. This file is heavily used by tests to execute the SP
  under test and assert results.

- **`tests/conftest.py`**: Defines pytest fixtures used across tests (e.g.
  `db_session` or `db_config`), configures logging, and may define command-line
  options for selecting test servers.

- **`tests/helpers/generic_query_helpers.py`**: Utility functions for building
  SQL query strings (e.g. `select_from_table`) used by multiple test modules.

- **`tests/helpers/sp_test_utils.py`**: Contains reusable logic for executing
  procedures and verifying responses. It may wrap `procedures.run_stored_procedure`
  and provide standardized assertions (e.g., checking return codes, row counts).

- **`tests/modules/test_create_01.py`** & **`test_edit_01.py`**: Example test
  files that demonstrate how to create data, call SPs with various parameters,
  and assert expected outcomes. They depend on JSON test data and validator
  files found in the same directory.

  The section below walks through `test_create_01.py` as a concrete example.

- **`tests/modules/schGroup_output_validator.py`**: Example validator script
  that inspects output from an SP and ensures that it matches expected
  patterns or values.

- **`contrib/` scripts**: Extra utilities such as `check_sp_parameters.py` or
  `db_inspect.py` for manual inspection; these are not required by the core
  test framework but can help with debugging or migrating.


### Example test walk‑through 🧪

Here’s how `tests/modules/test_create_01.py` is structured and what each piece
is doing:

1. **Imports** — bring in pytest, helper functions and validators:
   ```python
   import pytest
   from tests.helpers.sp_test_utils import run_stored_procedures
   from tests.helpers.preseed_utils import verify_preseed_exists
   from tests.modules.schGroup_output_validator import (
       getSchdGrpDetails,
       validateSchdGrpActive,
       getSchdGrpHistory,
       validateSchdGrpHistoryExists,
   )
   from tests.enums.test_enums import TestCaseType
   ```

2. **Constants** — fixed values used across tests (e.g. `TEST_USER_ID`).
3. **Fixture `created_team_id`**
   - Uses `db_transaction` fixture to run inside a rollbackable transaction.
   - Verifies that prerequisite rows are present by calling
     `verify_preseed_exists` with SQL files placed alongside the test.
   - Calls `run_stored_procedures` which actually executes the SP under test
     (`usp_CreateUpdateSchedulingTeam`) using JSON data from
     `createSchdGroup_testData.json`.
   - Asserts that an ID was returned and yields it to dependent tests.

4. **Test `test_history_create_update`**
   - Fetches the newly created team with `getSchdGrpDetails` and ensures it
     exists.
   - Queries history records and asserts that the creation event is present
     using helper validators.
   - Because the test runs in a database transaction, no manual cleanup is
     needed; the rollback at the end removes the row.

5. **Test `test_active_flag`**
   - Simple assertion that the active‑flag logic works via
     `validateSchdGrpActive`.

This example highlights common patterns:

- Use reusable fixtures for setup/teardown
- Keep test data external (JSON or SQL files)
- Leverage validators to encapsulate complex assertions
- Track shared constants (like user IDs) at the top of the file

---

## Tips for contributors ✍️

- Keep helpers generic; avoid hardcoding SP names or table names whenever
  possible.
- When adding new dependencies, update `requirements.txt` and confirm tests
  pass in a clean venv.
- Document new scripts or modules in this README or in `contrib/` with a
  markdown file.
- Run `black` or your preferred formatter on changed files to maintain style.

---

> _This README is intended to give a newcomer enough context to start working
> with the SP validation framework and to understand which files are necessary
> for writing and running tests._

Feel free to expand sections or add project-specific details as the codebase
evolves. Happy testing! 🎉