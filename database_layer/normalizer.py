"""SQL Type Normalizer - Converts Python values to SQL-compatible formats."""

from datetime import datetime, date, time
import logging
from typing import Any, Dict, Optional
import re

logger = logging.getLogger(__name__)


def _looks_like_date(value: str) -> bool:
    """Check if a string value looks like a date."""
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
        """Normalize a parameter value for SQL execution."""
        if value is None:
            return None
        
        if sql_type is None:
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
            
            # Integer types
            elif target_type in (SQLDataType.INT, SQLDataType.BIGINT,
                                SQLDataType.SMALLINT, SQLDataType.TINYINT):
                if isinstance(value, str):
                    value_stripped = value.strip()
                    
                    if _looks_like_date(value_stripped):
                        logger.debug(
                            f"Parameter '{param_name}' has date string '{value}' "
                            f"but SQL type is {target_type} - returning as-is"
                        )
                        return value
                    
                    if value_stripped == '':
                        return 0
                    
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
            
            # Bit type
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
            
            # Decimal type
            elif target_type in (SQLDataType.DECIMAL, SQLDataType.NUMERIC,
                                SQLDataType.MONEY, SQLDataType.SMALLMONEY):
                if isinstance(value, str) and value.strip() == '':
                    return 0
                return value
            
            return value
        
        except Exception as e:
            logger.warning(
                f"Failed to normalize parameter '{param_name}' with value '{value}' "
                f"to type '{target_type}': {str(e)}"
            )
            return value

    @staticmethod
    def _normalize_date(value: Any) -> Any:
        """Format date values to SQL date format (YYYY-MM-DD)."""
        if isinstance(value, date) and not isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')
        if isinstance(value, int) and value == 0:
            return None
        return value

    @staticmethod
    def _normalize_time(value: Any) -> Any:
        """Format time values to SQL time format (HH:MM:SS)."""
        if isinstance(value, time):
            return value.strftime('%H:%M:%S')
        if isinstance(value, datetime):
            return value.strftime('%H:%M:%S')
        return value

    @staticmethod
    def _normalize_datetime(value: Any) -> Any:
        """Format datetime values to SQL datetime format (YYYY-MM-DD HH:MM:SS)."""
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(value, date):
            return f"{value.strftime('%Y-%m-%d')} 00:00:00"
        if isinstance(value, int) and value == 0:
            return None
        return value


class ParameterNormalizer:
    """Normalize all parameters in a dictionary for SQL execution."""

    @staticmethod
    def normalize_parameters(parameters: Dict[str, Any], 
                            type_mappings: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Normalize all parameters in a dictionary."""
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
                normalized[param_name] = value
        
        return normalized
