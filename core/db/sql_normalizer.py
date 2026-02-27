"""
SQL Type Normalizer - Converts Python values to SQL-compatible formats.

This module normalizes parameter values based on explicit SQL data types from
database metadata. It handles formatting (especially for date/time types) to
ensure proper SQL Server execution. Values are NOT converted between types;
only formatting is applied when explicit SQL type metadata is provided.
"""

from datetime import datetime, date, time
import logging
from typing import Any, Dict, Optional
import re

logger = logging.getLogger(__name__)


def _looks_like_date(value: str) -> bool:
    """Check if a string value looks like a date.
    
    Matches patterns like:
    - 1900-01-01 (ISO)
    - 01/01/1900 (various formats)
    - Jan 1 1900
    - 1/1/1900
    """
    if not isinstance(value, str):
        return False
    
    value = value.strip()
    
    # ISO format: YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}', value):
        return True
    
    # SQL datetime format: YYYY-MM-DD HH:MM:SS
    if re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', value):
        return True
    
    # Various other date formats with slashes
    if re.match(r'^\d{1,2}/\d{1,2}/\d{2,4}', value):
        return True
    
    # Month name formats: Jan 1 1900, Dec 30 1995
    if re.match(r'^[A-Za-z]{3}\s+\d{1,2}\s+\d{4}', value):
        return True
    
    # Month name with time: Jan 1 1900 12:00AM
    if re.match(r'^[A-Za-z]{3}\s+\d{1,2}\s+\d{4}\s+\d{1,2}:\d{2}', value):
        return True
    
    return False


class SQLDataType:
    """SQL Server data types enumeration."""
    INT = "INT"
    BIGINT = "BIGINT"
    SMALLINT = "SMALLINT"
    TINYINT = "TINYINT"
    FLOAT = "FLOAT"
    DECIMAL = "DECIMAL"
    NUMERIC = "NUMERIC"
    BIT = "BIT"
    CHAR = "CHAR"
    VARCHAR = "VARCHAR"
    NCHAR = "NCHAR"
    NVARCHAR = "NVARCHAR"
    TEXT = "TEXT"
    NTEXT = "NTEXT"
    DATE = "DATE"
    TIME = "TIME"
    DATETIME = "DATETIME"
    DATETIME2 = "DATETIME2"
    DATETIMEOFFSET = "DATETIMEOFFSET"
    SMALLDATETIME = "SMALLDATETIME"
    MONEY = "MONEY"
    SMALLMONEY = "SMALLMONEY"
    BINARY = "BINARY"
    VARBINARY = "VARBINARY"


class SQLNormalizer:
    """Normalize Python values to SQL-compatible formats based on explicit SQL type metadata."""

    @staticmethod
    def normalize(param_name: str, value: Any, sql_type: Optional[str] = None) -> Any:
        """
        Normalize a parameter value for SQL execution.
        
        Only performs normalization if an explicit SQL type is provided.
        Without explicit type metadata, values are returned unchanged to preserve
        their original types and prevent incorrect conversions.
        
        Args:
            param_name: Parameter name
            value: Original value
            sql_type: Explicit SQL type from database metadata (required for normalization)
        
        Returns:
            Normalized value if sql_type provided, otherwise original value unchanged
        """
        if value is None:
            return None
        
        # Only normalize if we have explicit SQL type information
        if sql_type is None:
            # No type metadata - return value unchanged
            logger.debug(f"No explicit SQL type for '{param_name}' - value returned unchanged")
            return value
        
        target_type = sql_type
        try:
            # Date types - format for SQL
            if target_type == SQLDataType.DATE:
                return SQLNormalizer._normalize_date(value)
            
            elif target_type in (SQLDataType.DATETIME, SQLDataType.DATETIME2,
                                 SQLDataType.SMALLDATETIME, SQLDataType.DATETIMEOFFSET):
                return SQLNormalizer._normalize_datetime(value)
            
            elif target_type == SQLDataType.TIME:
                return SQLNormalizer._normalize_time(value)
            
            # Integer types - must convert strings to avoid SQL Server errors
            elif target_type in (SQLDataType.INT, SQLDataType.BIGINT,
                                SQLDataType.SMALLINT, SQLDataType.TINYINT):
                if isinstance(value, str):
                    value_stripped = value.strip()
                    
                    # Check if it's a date string - if so, don't convert to int
                    if _looks_like_date(value_stripped):
                        logger.debug(
                            f"Parameter '{param_name}' has date string '{value}' "
                            f"but SQL type is {target_type} - returning as-is"
                        )
                        return value
                    
                    # Handle empty strings
                    if value_stripped == '':
                        return 0
                    
                    # Try to parse numeric strings
                    try:
                        return int(float(value_stripped))
                    except ValueError:
                        logger.warning(f"Cannot convert string '{value}' to int, passing as-is")
                        return value
                elif isinstance(value, bool):
                    return 1 if value else 0
                elif isinstance(value, float):
                    return int(value)
                return value
            
            # Bit type - convert appropriately
            elif target_type == SQLDataType.BIT:
                if isinstance(value, str):
                    if value.strip() == '':
                        return 0
                    try:
                        return 1 if int(value) != 0 else 0
                    except ValueError:
                        return value
                elif isinstance(value, bool):
                    return 1 if value else 0
                elif isinstance(value, int):
                    return 1 if value != 0 else 0
                return value
            
            # Decimal type - handle empty strings
            elif target_type in (SQLDataType.DECIMAL, SQLDataType.NUMERIC,
                                SQLDataType.MONEY, SQLDataType.SMALLMONEY):
                if isinstance(value, str) and value.strip() == '':
                    return 0
                return value
            
            # For all other types, return value unchanged
            logger.debug(
                f"No format conversion for '{param_name}' type '{target_type}' - "
                f"value returned unchanged: {repr(value)}"
            )
            return value
        
        except Exception as e:
            logger.warning(
                f"Failed to normalize parameter '{param_name}' with value '{value}' "
                f"to type '{target_type}': {str(e)}"
            )
            return value

    @staticmethod
    def _normalize_date(value: Any) -> Any:
        """
        Format date values to SQL date format (YYYY-MM-DD).
        
        Handles:
        - date/datetime objects: formatted to YYYY-MM-DD
        - String dates: returned as-is (may be ISO, US, or SQL formats)
        - Integer 0: converted to NULL (common for unset date parameters)
        - Other numeric: returned as-is
        """
        if isinstance(value, date) and not isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')
        # Handle 0 as NULL for unset date fields
        if isinstance(value, int) and value == 0:
            return None
        # Return strings and other types unchanged
        return value

    @staticmethod
    def _normalize_time(value: Any) -> Any:
        """
        Format time values to SQL time format (HH:MM:SS).
        
        Only formats actual time/datetime objects. Other types are returned
        unchanged.
        """
        if isinstance(value, time):
            return value.strftime('%H:%M:%S')
        if isinstance(value, datetime):
            return value.strftime('%H:%M:%S')
        # Return other types unchanged
        return value

    @staticmethod
    def _normalize_datetime(value: Any) -> Any:
        """
        Format datetime values to SQL datetime format (YYYY-MM-DD HH:MM:SS).
        
        Handles:
        - datetime objects: formatted to YYYY-MM-DD HH:MM:SS
        - date objects: formatted with midnight time
        - Integer 0: converted to NULL
        - String dates: returned as-is (may need SQL Server to parse)
        """
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(value, date):
            return f"{value.strftime('%Y-%m-%d')} 00:00:00"
        # Handle 0 as NULL for unset datetime fields
        if isinstance(value, int) and value == 0:
            return None
        # Return strings and other types unchanged
        # SQL Server can parse various datetime formats
        return value


class ParameterNormalizer:
    """Normalize all parameters in a dictionary for SQL execution."""

    @staticmethod
    def normalize_parameters(parameters: Dict[str, Any], 
                            type_mappings: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Normalize all parameters in a dictionary.
        
        Args:
            parameters: Dictionary of parameter name -> value
            type_mappings: Optional dictionary of parameter name -> SQL type
        
        Returns:
            Dictionary with normalized values
        """
        if not parameters:
            return {}
        
        normalized = {}
        type_mappings = type_mappings or {}
        
        for param_name, value in parameters.items():
            try:
                sql_type = type_mappings.get(param_name)
                normalized_value = SQLNormalizer.normalize(param_name, value, sql_type)
                normalized[param_name] = normalized_value
                
                if normalized_value != value:
                    logger.debug(
                        f"Normalized '{param_name}': {type(value).__name__}({repr(value)}) "
                        f"-> {type(normalized_value).__name__}({repr(normalized_value)})"
                    )
            
            except Exception as e:
                logger.error(f"Error normalizing parameter '{param_name}': {str(e)}")
                # Keep original value if normalization fails
                normalized[param_name] = value
        
        return normalized

    @staticmethod
    def normalize_from_test_case(test_case: Dict[str, Any], 
                                 type_mappings: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Normalize parameters from a test case dictionary.
        
        Args:
            test_case: Test case dictionary with 'parameters' key
            type_mappings: Optional dictionary of parameter name -> SQL type
        
        Returns:
            Dictionary with normalized parameters
        """
        parameters = test_case.get('parameters', {})
        return ParameterNormalizer.normalize_parameters(parameters, type_mappings)


def normalize_sp_parameters(sp_name: str, parameters: Dict[str, Any],
                           type_mappings: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Convenience function to normalize stored procedure parameters.
    
    Args:
        sp_name: Stored procedure name
        parameters: Dictionary of parameters
        type_mappings: Optional type mappings
    
    Returns:
        Normalized parameters
    """
    logger.info(f"Normalizing parameters for SP: {sp_name}")
    normalized = ParameterNormalizer.normalize_parameters(parameters, type_mappings)
    logger.debug(f"Normalized parameters: {normalized}")
    return normalized
