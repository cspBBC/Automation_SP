from core.db.connection import DBSession
from core.db.sql_normalizer import ParameterNormalizer, SQLDataType
import logging

logger = logging.getLogger(__name__)

def get_stored_procedure_parameters(sp_name):
    """Get parameter metadata for a stored procedure.
    
    Args:
        sp_name: Name of the stored procedure
    
    Returns:
        List of tuples: (PARAMETER_NAME, DATA_TYPE, PARAMETER_MODE)
    """
    with DBSession() as db:
        query = """
        SELECT PARAMETER_NAME, DATA_TYPE, PARAMETER_MODE
        FROM INFORMATION_SCHEMA.PARAMETERS
        WHERE SPECIFIC_NAME = ?
        ORDER BY ORDINAL_POSITION
        """
        return db.execute_query(query, (sp_name,))

def _build_type_mappings_from_metadata(sp_name):
    """Build parameter type mappings from SP metadata in the database.
    
    Args:
        sp_name: Name of the stored procedure
    
    Returns:
        Dictionary mapping @parameter_name -> SQL_TYPE
    """
    try:
        param_rows = get_stored_procedure_parameters(sp_name)
        if not param_rows:
            logger.warning(f"No parameter metadata found for SP '{sp_name}'")
            return {}
        
        type_mappings = {}
        for row in param_rows:
            # row format: (PARAMETER_NAME, DATA_TYPE, PARAMETER_MODE)
            param_name = row[0]
            data_type = row[1].upper()
            
            # Map SQL Server types to SQLDataType
            # Common overrides for data type normalization
            if data_type in ('INT', 'BIGINT', 'SMALLINT', 'TINYINT'):
                type_mappings[param_name] = SQLDataType.INT
            elif data_type in ('FLOAT', 'REAL'):
                type_mappings[param_name] = SQLDataType.FLOAT
            elif data_type in ('DECIMAL', 'NUMERIC', 'MONEY', 'SMALLMONEY'):
                type_mappings[param_name] = SQLDataType.DECIMAL
            elif data_type in ('BIT',):
                type_mappings[param_name] = SQLDataType.BIT
            elif data_type in ('VARCHAR', 'CHAR'):
                type_mappings[param_name] = SQLDataType.VARCHAR
            elif data_type in ('NVARCHAR', 'NCHAR'):
                type_mappings[param_name] = SQLDataType.NVARCHAR
            elif data_type in ('DATE',):
                type_mappings[param_name] = SQLDataType.DATE
            elif data_type in ('DATETIME', 'DATETIME2', 'SMALLDATETIME', 'DATETIMEOFFSET'):
                type_mappings[param_name] = SQLDataType.DATETIME
            elif data_type in ('TIME',):
                type_mappings[param_name] = SQLDataType.TIME
            else:
                # For unknown types, use the data_type as-is
                type_mappings[param_name] = data_type
        
        logger.debug(f"Built type mappings for SP '{sp_name}': {type_mappings}")
        return type_mappings
    
    except Exception as e:
        logger.warning(f"Failed to fetch parameter metadata for SP '{sp_name}': {str(e)}")
        return {}

def list_stored_procedures():
    with DBSession() as db:
        query = """
        SELECT SPECIFIC_NAME
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_TYPE='PROCEDURE' AND SPECIFIC_NAME LIKE '%group%'
        ORDER BY SPECIFIC_NAME
        """
        return [row[0] for row in db.execute_query(query)]

def run_stored_procedure(sp_name, params=None, type_mappings=None, capture_output_params=False):
    """Execute a stored procedure with automatic parameter normalization.

    * If ``params`` is a sequence (list/tuple), values are bound positionally.
    * If ``params`` is a dict, keys are treated as parameter names and the
      SQL is built as ``@name=?,@name2=?`` etc.  The values are taken in the
      same order as the keys to ensure proper binding.
    * Parameters are automatically normalized based on SP metadata from the database
      to ensure proper formatting and prevent execution errors.

    Args:
        sp_name: Name of the stored procedure
        params: Parameters (None, sequence, or dict)
        type_mappings: Optional dict of param_name -> SQL type. If not provided,
                      will fetch from database SP metadata.
        capture_output_params: If True, return dict with 'rows' and 'output_params'
                             If False (default), return list of rows

    Returns:
        If capture_output_params=False: List of result rows
        If capture_output_params=True: Dict with 'rows' and 'output_params' keys
    """
    with DBSession() as db:
        if params is None:
            sql = f"EXEC {sp_name}"
            result_rows = db.execute_query(sql)
            return _format_result(result_rows, None, capture_output_params)

        # positional parameters
        if isinstance(params, (list, tuple)):
            placeholders = ",".join("?" for _ in params)
            sql = f"EXEC {sp_name} {placeholders}"
            result_rows = db.execute_query(sql, params)
            return _format_result(result_rows, None, capture_output_params)

        # named parameters - normalize before execution
        if isinstance(params, dict):
            # Get type mappings from SP metadata if not explicitly provided
            if type_mappings is None:
                type_mappings = _build_type_mappings_from_metadata(sp_name)
            
            # Normalize all parameters based on their SQL types
            normalized_params = ParameterNormalizer.normalize_parameters(params, type_mappings)
            logger.info(f"Executing SP '{sp_name}' with {len(normalized_params)} parameters")
            logger.debug(f"Normalized params: {normalized_params}")
            
            # preserve insertion order (guaranteed by Python 3.7+)
            names = list(normalized_params.keys())
            placeholders = ",".join(f"{name}=?" for name in names)
            sql = f"EXEC {sp_name} {placeholders}"
            values = [normalized_params[name] for name in names]
            result_rows = db.execute_query(sql, values)
            
            # Extract output params if requested
            output_params = None
            if capture_output_params:
                output_params = db.get_output_params()
            
            return _format_result(result_rows, output_params, capture_output_params)

        raise TypeError("params must be None, sequence or dict")

def _format_result(rows, output_params, capture_output_params):
    """Format result based on capture_output_params flag."""
    if capture_output_params:
        return {
            'rows': rows,
            'output_params': output_params or {}
        }
    return rows

def get_stored_procedure_details(sp_name):
    with DBSession() as db:
        # First, check if the stored procedure exists
        check_query = """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE SPECIFIC_NAME = ? AND ROUTINE_TYPE = 'PROCEDURE'
        """
        exists = db.execute_query(check_query, (sp_name,))[0][0]

        if exists:
            print(f"Stored procedure '{sp_name}' exists in the database.")
            query = """
            SELECT SPECIFIC_NAME, ROUTINE_DEFINITION, ROUTINE_TYPE, CREATED, LAST_ALTERED
            FROM INFORMATION_SCHEMA.ROUTINES
            WHERE SPECIFIC_NAME = ? AND ROUTINE_TYPE = 'PROCEDURE'
            """
            return db.execute_query(query, (sp_name,))
        else:
            print(f"Stored procedure '{sp_name}' does not exist in the database.")
            return None