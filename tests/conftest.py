import os
import datetime
import pytest
import logging
from test_engine_layer.utils import setup_logging, validate_test_configuration


setup_logging()  # Initialize logger for all tests


def pytest_configure(config):
    """Configure pytest - validate test configuration before any tests run."""
    # Validate test configuration (works with CSV/XLSX/JSON any format)
    try:
        validate_test_configuration()
    except AssertionError as e:
        pytest.exit(f"Configuration validation failed:\n{e}", returncode=1)
    
    # Auto-detect worker count if not specified
    if not hasattr(config.option, 'numprocesses') or config.option.numprocesses is None:
        import multiprocessing
        config.option.numprocesses = max(2, multiprocessing.cpu_count() - 1)
    
    # Mark as CI environment if CI env var is set
    config.ci_mode = os.environ.get('CI', '').lower() in ['true', '1', 'yes']


def pytest_addoption(parser):
    parser.addoption(
        "--output-dir",
        action="store",
        default="output",
        help="Base folder where per-test output directories are created",
    )


@pytest.fixture
def logger(request):
    """Provide logger to tests - already initialized by setup_logging()."""
    return logging.getLogger('sp_validation')


@pytest.fixture
def db_transaction(request):
    """Fixture to enable transaction-based test isolation.
    
    Starts a transaction before the test and rolls it back afterwards.
    All DBSession instances used during the test will use the same
    transaction context, ensuring complete isolation.
    """
    from database_layer.connection import get_connection
    from database_layer.transaction_manager import set_test_transaction, clear_test_transaction
    
    # Get a connection for this test
    conn = get_connection()
    set_test_transaction(conn)
    
    yield conn
    
    # Rollback and cleanup
    try:
        conn.rollback()
    finally:
        conn.close()
        clear_test_transaction()


@pytest.fixture
def output_dir(request):
    """Return a unique directory for the current test.

    The path is constructed from the base ``--output-dir`` option plus the fully
    qualified test node id (with ``::`` replaced by ``/``).  It is created on
    first access.  Tests can write additional files there (logs, debug output,
    JSON dumps, etc.).
    """
    base = request.config.getoption("--output-dir")
    # sanitize nodeid (replace invalid chars)
    node_path = request.node.nodeid.replace("::", os.sep).replace("/", os.sep)
    dir_path = os.path.join(base, node_path)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


@pytest.fixture(autouse=True)
def setup_execution_logging(request, output_dir):
    """Setup file logging to execution.log for all test output.
    
    Parallel-safe: uses pytest-xdist worker ID if available.
    """
    # Get the sp_validation logger (tests use this)
    test_logger = logging.getLogger('sp_validation')
    
    # Get worker ID for parallel execution (empty string if not running in parallel)
    worker_id = getattr(request.config, 'workerinput', {}).get('workerid', 'master')
    
    # Create file handler with worker ID in filename for parallel safety
    log_file = os.path.join(output_dir, f"execution_{worker_id}.log")
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add file handler directly to sp_validation logger (not root)
    test_logger.addHandler(file_handler)
    
    yield
    
    file_handler.close()
    test_logger.removeHandler(file_handler)


@pytest.fixture(autouse=True)
def capture_stdout_to_file(request, output_dir, capsys):
    """Automatically dump captured stdout/stderr to a file in the output dir.

    This fixture is `autouse` so every test gets its output stored.
    """
    yield
    # after test finishes, write captured output
    out, err = capsys.readouterr()
    if out:
        with open(os.path.join(output_dir, "stdout.txt"), "w", encoding="utf-8") as f:
            f.write(out)
    if err:
        with open(os.path.join(output_dir, "stderr.txt"), "w", encoding="utf-8") as f:
            f.write(err)

