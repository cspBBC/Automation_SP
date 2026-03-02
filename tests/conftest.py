import os
import datetime
import pytest


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

