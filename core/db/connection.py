import pyodbc
import threading
from config.config import DatabaseConfig

# Thread-local storage for test-level transactions
_test_transaction = threading.local()

class DBSession:
    def __enter__(self):
        DatabaseConfig.validate()
        
        # Check if we're in a test transaction context
        # This ensures all queries see the same transaction.
        if hasattr(_test_transaction, 'conn') and _test_transaction.conn:
            # Use the existing test transaction connection
            self.conn = _test_transaction.conn
            self.cursor = self.conn.cursor()
            self._is_test_txn = True
        else:
            # Create a new connection
            self.conn = pyodbc.connect(
                f"DRIVER={{SQL Server}};"
                f"SERVER={DatabaseConfig.DB_HOST};"
                f"DATABASE={DatabaseConfig.DB_NAME};"
                f"UID={DatabaseConfig.DB_USER};"
                f"PWD={DatabaseConfig.DB_PASSWORD}"
            )
            self.cursor = self.conn.cursor()
            self._is_test_txn = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Only manage transaction if this session created the connection
        if not self._is_test_txn:
            if exc_type is None:
                # No exception - commit the transaction
                self.conn.commit()
            else:
                # Exception occurred - rollback
                self.conn.rollback()
            self.cursor.close()
            self.conn.close()
        # If this is a test transaction, don't close or commit - let the fixture handle it

    def execute_query(self, query, params=None):
        self.cursor.execute(query, params or [])
        return self.cursor.fetchall()
    
    def get_output_params(self):
        """Get output parameters from the last executed query.
        
        pyodbc stores output parameters in cursor.output_params as a dictionary.
        """
        try:
            if hasattr(self.cursor, 'output_params'):
                return self.cursor.output_params
            return {}
        except Exception as e:
            import logging
            logging.debug(f"Could not retrieve output parameters: {e}")
            return {}


def set_test_transaction(conn):
    """Set the test transaction connection (called by pytest fixture)."""
    _test_transaction.conn = conn


def clear_test_transaction():
    """Clear the test transaction connection (called by pytest fixture)."""
    _test_transaction.conn = None


def get_connection():
    """Get a raw pyodbc connection (not a context manager)."""
    DatabaseConfig.validate()
    conn = pyodbc.connect(
        f"DRIVER={{SQL Server}};"
        f"SERVER={DatabaseConfig.DB_HOST};"
        f"DATABASE={DatabaseConfig.DB_NAME};"
        f"UID={DatabaseConfig.DB_USER};"
        f"PWD={DatabaseConfig.DB_PASSWORD}"
    )
    return conn