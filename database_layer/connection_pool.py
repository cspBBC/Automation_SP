"""Connection Pool - Manages database connection pooling."""

import pyodbc
import logging
from config.config import DatabaseConfig

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Simple connection pool for database connections."""
    
    _instance = None
    
    def __init__(self, pool_size: int = 5):
        """Initialize connection pool.
        
        Args:
            pool_size: Maximum number of connections to maintain
        """
        self.pool_size = pool_size
        self.connections = []
        self.available = []
    
    @classmethod
    def get_instance(cls, pool_size: int = 5):
        """Get singleton instance of connection pool."""
        if cls._instance is None:
            cls._instance = cls(pool_size)
        return cls._instance
    
    def acquire_connection(self):
        """Acquire a connection from the pool."""
        DatabaseConfig.validate()
        
        if self.available:
            return self.available.pop()
        
        if len(self.connections) < self.pool_size:
            conn = pyodbc.connect(
                f"DRIVER={{SQL Server}};"
                f"SERVER={DatabaseConfig.DB_HOST};"
                f"DATABASE={DatabaseConfig.DB_NAME};"
                f"UID={DatabaseConfig.DB_USER};"
                f"PWD={DatabaseConfig.DB_PASSWORD}"
            )
            self.connections.append(conn)
            return conn
        
        # Wait for a connection to become available
        if self.available:
            return self.available.pop()
        
        raise RuntimeError("Connection pool exhausted")
    
    def release_connection(self, conn):
        """Release a connection back to the pool."""
        if conn:
            self.available.append(conn)
    
    def close_all(self):
        """Close all connections in the pool."""
        for conn in self.connections:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
        self.connections.clear()
        self.available.clear()
