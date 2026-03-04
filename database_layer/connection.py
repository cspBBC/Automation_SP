"""Connection Manager - Manages database connections."""

import pyodbc
import logging
from config.config import DatabaseConfig
from database_layer.transaction_manager import get_test_transaction

logger = logging.getLogger('sp_validation')


class DBSession:
    """Context manager for database sessions."""
    
    def __enter__(self):
        DatabaseConfig.validate()
        
        # Check if we're in a test transaction context
        test_transaction = get_test_transaction()
        if test_transaction:
            self.conn = test_transaction
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
        """Execute a query and return all results."""
        self.cursor.execute(query, params or [])
        return self.cursor.fetchall()
    
    def get_output_params(self):
        """Get output parameters from the last executed query."""
        try:
            if hasattr(self.cursor, 'output_params'):
                return self.cursor.output_params
            return {}
        except Exception as e:
            logger.debug(f"Could not retrieve output parameters: {e}")
            return {}


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
