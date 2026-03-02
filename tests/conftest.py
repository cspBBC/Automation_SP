import os
import datetime
import pytest
import logging


def pytest_addoption(parser):
    parser.addoption(
        "--output-dir",
        action="store",
        default="output",
        help="Base folder where per-test output directories are created",
    )


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
    
    Captures all logger output and writes it to execution.log in the output 
    directory. This creates a complete transcript of all test execution steps.
    """
    # Get root logger and set to DEBUG to capture everything
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Create file handler for execution.log
    log_file = os.path.join(output_dir, "execution.log")
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatter that includes timestamp and level
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add file handler to root logger
    root_logger.addHandler(file_handler)
    
    yield
    
    # Cleanup
    file_handler.close()
    root_logger.removeHandler(file_handler)


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

