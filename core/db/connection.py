import pyodbc
from config.config import DatabaseConfig

class DBSession:
    def __enter__(self):
        DatabaseConfig.validate()
        self.conn = pyodbc.connect(
            f"DRIVER={{SQL Server}};"
            f"SERVER={DatabaseConfig.DB_HOST};"
            f"DATABASE={DatabaseConfig.DB_NAME};"
            f"UID={DatabaseConfig.DB_USER};"
            f"PWD={DatabaseConfig.DB_PASSWORD}"
        )
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # No exception - commit the transaction
            self.conn.commit()
        else:
            # Exception occurred - rollback
            self.conn.rollback()
        self.cursor.close()
        self.conn.close()

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