"""Transaction Manager - Manages database transactions."""

import threading
import logging

logger = logging.getLogger(__name__)

# Thread-local storage for test-level transactions
_test_transaction = threading.local()


def set_test_transaction(conn):
    """Set the test transaction connection (called by pytest fixture)."""
    _test_transaction.conn = conn
    logger.debug("Test transaction context set")


def clear_test_transaction():
    """Clear the test transaction connection (called by pytest fixture)."""
    _test_transaction.conn = None
    logger.debug("Test transaction context cleared")


def get_test_transaction():
    """Get the current test transaction connection if set."""
    return getattr(_test_transaction, 'conn', None)


class TransactionManager:
    """Manages database transactions."""
    
    @staticmethod
    def is_in_test_transaction():
        """Check if currently in a test transaction context."""
        return hasattr(_test_transaction, 'conn') and _test_transaction.conn is not None
    
    @staticmethod
    def get_current_transaction():
        """Get the current transaction connection."""
        return get_test_transaction()
