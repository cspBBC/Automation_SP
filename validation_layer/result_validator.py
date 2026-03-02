"""Result Validator - Orchestrates result validation."""

from typing import Dict, List, Any
import logging
from test_engine_layer.utils import Colors
from test_engine_layer.parameter_manager import format_dict

logger = logging.getLogger(__name__)


def row_to_dict(row, col_names=None) -> Dict:
    """Convert a database row to dictionary."""
    if isinstance(row, dict):
        return row
    
    if col_names:
        try:
            row_list = list(row)
            if len(col_names) == len(row_list):
                return dict(zip(col_names, row_list))
        except Exception:
            pass
    
    try:
        if hasattr(row, 'keys'):
            col_names_from_row = list(row.keys())
            result = {}
            for i, col_name in enumerate(col_names_from_row):
                try:
                    val = row[col_name]
                    result[col_name] = val
                except Exception:
                    try:
                        val = row[i]
                        result[col_name] = val
                    except Exception:
                        result[col_name] = None
            return result if result else row
    except Exception:
        pass
    
    return row


def validate_post_state(results: List, expected_config: List[Dict], context: Dict, logger=None) -> bool:
    """Validate post-SQL results against expected post-state.
    
    Args:
        results: List of (rows, col_names) tuples from SQL execution
        expected_config: List of dicts with expectations
        context: Context dict for value formatting
        logger: Optional logger
        
    Returns:
        True if all validations pass, False otherwise
    """
    def _log_msg(msg, use_colors=False):
        if logger:
            clean_msg = msg
            for color_code in [Colors.RED, Colors.GREEN, Colors.YELLOW, Colors.BLUE, Colors.RESET, Colors.BOLD]:
                clean_msg = clean_msg.replace(color_code, '')
            clean_msg = clean_msg.replace('✓', '[PASS]').replace('✗', '[FAIL]')
            logger.info(clean_msg)
        else:
            print(msg)
    
    _log_msg(f"\n{'='*80}")
    _log_msg(Colors.info("VALIDATING POST-STATE"))
    _log_msg(f"{'='*80}")
    
    if not isinstance(expected_config, list):
        expected_config = [expected_config]
    
    all_pass = True
    validation_summary = []
    
    for idx, result_tuple in enumerate(results):
        _log_msg(f"\n[Query {idx + 1}] Validating result set...")
        query_pass = True
        
        if isinstance(result_tuple, tuple) and len(result_tuple) == 2:
            result_set, col_names = result_tuple
        else:
            result_set = result_tuple
            col_names = []
        
        if idx >= len(expected_config):
            _log_msg(f"  {Colors.warn('[WARN]')} (no expected_config for query {idx + 1})")
            continue
        
        expected = expected_config[idx]
        
        if result_set is None:
            msg = f"  {Colors.fail('[FAIL]')} Query execution failed (no results)"
            _log_msg(msg)
            validation_summary.append((f"Query {idx + 1}", False))
            all_pass = False
            continue
        
        # Check row count if specified
        if 'row_count' in expected:
            expected_count = expected['row_count']
            actual_count = len(result_set)
            if actual_count == expected_count:
                msg = f"  {Colors.success('[PASS]')} Row count: {actual_count} (expected {expected_count})"
                _log_msg(msg)
            else:
                msg = f"  {Colors.fail('[FAIL]')} Row count: {actual_count} (expected {expected_count})"
                _log_msg(msg)
                query_pass = False
                all_pass = False
        
        # Check specific columns if specified
        if 'expected_columns' in expected and result_set and len(result_set) > 0:
            first_row = result_set[0]
            row_dict = row_to_dict(first_row, col_names=col_names)
            
            if isinstance(row_dict, dict):
                available_keys = list(row_dict.keys())
                _log_msg(f"  [DEBUG] Available columns: {available_keys[:5]}...")
            
            expected_cols = expected['expected_columns']
            expected_cols = format_dict(expected_cols, context) if isinstance(expected_cols, dict) else expected_cols
            
            for col_name, expected_val in expected_cols.items():
                actual_val = None
                
                if isinstance(row_dict, dict):
                    if col_name in row_dict:
                        actual_val = row_dict[col_name]
                    else:
                        for key in row_dict.keys():
                            if key.lower() == col_name.lower():
                                actual_val = row_dict[key]
                                break
                
                if actual_val == expected_val:
                    msg = f"  {Colors.success('[PASS]')} {col_name}: {actual_val}"
                    _log_msg(msg)
                else:
                    msg = f"  {Colors.fail('[FAIL]')} {col_name}: {actual_val} (expected {expected_val})"
                    _log_msg(msg)
                    query_pass = False
                    all_pass = False
        
        validation_summary.append((f"Query {idx + 1}", query_pass))
    
    _log_msg(f"\n{'='*80}")
    _log_msg("VALIDATION SUMMARY")
    _log_msg(f"{'='*80}\n")
    
    for query_name, passed in validation_summary:
        if passed:
            status = Colors.success("[PASS]")
            display = f"  {status}  {query_name}"
        else:
            status = Colors.fail("[FAIL]")
            display = f"  {status}  {query_name}"
        _log_msg(display)
    
    _log_msg(f"\n{'='*80}")
    if all_pass:
        final_msg = Colors.success("ALL VALIDATIONS PASSED")
    else:
        final_msg = Colors.fail("SOME VALIDATIONS FAILED")
    _log_msg(final_msg)
    _log_msg(f"{'='*80}\n")
    
    return all_pass
