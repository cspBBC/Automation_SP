"""Connection Manager - Manages database connections."""

import pyodbc
import logging
import re
from config.config import DatabaseConfig
from database_layer.transaction_manager import get_test_transaction

logger = logging.getLogger('sp_validation')


class ParameterValidationError(Exception):
    """Custom exception for parameter validation errors with detailed information."""
    
    def __init__(self, message, parameter_name=None, value=None, error_type=None):
        self.message = message
        self.parameter_name = parameter_name
        self.value = value
        self.error_type = error_type
        super().__init__(self.format_message())
    
    def format_message(self):
        """Format error message with parameter-specific details."""
        if self.parameter_name:
            return f"Parameter '{self.parameter_name}' validation failed: {self.message} (value: {self.value})"
        return self.message


def parse_sql_error(error_message, params_dict=None):
    """Parse SQL error message to identify problematic parameter.
    
    Args:
        error_message: The SQL error message from pyodbc
        params_dict: Dictionary of parameters that were passed
    
    Returns:
        Tuple of (parsed_message, parameter_name, problematic_value, error_type)
    """
    params_dict = params_dict or {}
    error_str = str(error_message).lower()
    parsed_msg = str(error_message)
    param_name = None
    param_value = None
    error_type = None
    
    # Try to extract parameter name from error message
    # Common patterns: "parameter @paramName", "column 'paramName'"
    param_patterns = [
        r"parameter\s+@?(\w+)",
        r"column\s+['\"]?(\w+)['\"]?",
        r"constraint\s+['\"]?(\w+)['\"]?",
        r"check\s+constraint\s+['\"]?(\w+)['\"]?",
    ]
    
    for pattern in param_patterns:
        match = re.search(pattern, error_str)
        if match:
            param_name = match.group(1)
            if param_name in params_dict:
                param_value = params_dict[param_name]
            break
    
    # Classify error type
    if "conversion" in error_str or "invalid" in error_str or "type" in error_str:
        error_type = "TYPE_CONVERSION"
    elif "constraint" in error_str or "check" in error_str:
        error_type = "CONSTRAINT_VIOLATION"
    elif "range" in error_str or "overflow" in error_str:
        error_type = "RANGE_ERROR"
    elif "not found" in error_str or "does not exist" in error_str:
        error_type = "NOT_FOUND"
    elif "duplicate" in error_str or "unique" in error_str:
        error_type = "UNIQUENESS_VIOLATION"
    else:
        error_type = "VALIDATION_ERROR"
    
    return parsed_msg, param_name, param_value, error_type


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
        """Execute a query and return all results.
        
        Raises:
            ParameterValidationError: If SQL validation fails with parameter details
        """
        params = params or []
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except pyodbc.DatabaseError as e:
            # Extract parameter information from query
            params_dict = self._extract_params_from_query(query, params)
            parsed_msg, param_name, param_value, error_type = parse_sql_error(str(e), params_dict)
            
            # Log detailed error information
            logger.error(f"Database Error: {parsed_msg}")
            logger.debug(f"Error Type: {error_type}")
            if param_name:
                logger.error(f"  Problematic Parameter: '{param_name}'")
                logger.error(f"  Value: {param_value}")
            logger.debug(f"  Query: {query}")
            logger.debug(f"  Parameters: {params_dict}")
            
            # Raise detailed error
            raise ParameterValidationError(
                parsed_msg, 
                parameter_name=param_name,
                value=param_value,
                error_type=error_type
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during query execution: {e}")
            raise
    
    def _extract_params_from_query(self, query, params):
        """Extract parameter names and values from EXEC query.
        
        Handles format: EXEC sp_name param1=?,param2=?,...
        """
        params_dict = {}
        try:
            # Match EXEC statement with named parameters
            exec_pattern = r"EXEC\s+\w+\s+(.+)"
            match = re.search(exec_pattern, query, re.IGNORECASE)
            
            if match:
                params_str = match.group(1)
                # Split by comma, find parameter names (before =)
                param_assignments = re.findall(r"(\w+)\s*=\s*\?", params_str)
                
                for i, param_name in enumerate(param_assignments):
                    if i < len(params):
                        params_dict[param_name] = params[i]
            
        except Exception as e:
            logger.debug(f"Could not extract parameters from query: {e}")
        
        return params_dict
    
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
