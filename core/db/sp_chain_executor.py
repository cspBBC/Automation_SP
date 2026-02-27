"""
SP Chain Executor - Execute chained stored procedures with parameter inheritance.
Supports smart parameter reuse and overrides for efficient chain testing.
"""

from typing import Dict, List, Any
import logging
import copy

logger = logging.getLogger(__name__)


class SPChainExecutor:
    """Execute chained SPs with parameter inheritance and overrides."""
    
    def __init__(self, connection):
        self.connection = connection
        self.execution_results = {}
        self.chain_data = {}
        self.base_parameters = {}
    
    def execute_chain(self, chain_config: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute chained SPs with smart parameter inheritance.
        
        - Step 1: Uses full parameters → stored as base
        - Step 2+: Inherits from Step 1, overrides only changed params
        - Stops on first failure and reports error clearly
        """
        try:
            for idx, step_config in enumerate(chain_config):
                step_num = step_config.get("step", idx + 1)
                sp_name = step_config["sp_name"]
                
                logger.info(f"\n{'='*80}")
                logger.info(f"[CHAIN STEP {step_num}] Executing {sp_name}...")
                
                # Build parameters with inheritance
                params = self._build_parameters_with_inheritance(
                    step_config,
                    step_num
                )
                
                logger.info(f"Final parameters: {len(params)} total")
                logger.info(f"  Parameter names: {sorted(params.keys())}")
                logger.debug(f"  All params: {params}")
                
                # Execute SP
                result = self._execute_sp(sp_name, params)
                self.execution_results[f"step_{step_num}"] = result
                
                # CHECK FOR FAILURES - SP returns (status, message, data)
                step_status, step_message = self._check_step_status(result, step_num)
                if not step_status:
                    # Step failed - log error and stop chain
                    logger.error(f"[STEP {step_num}] FAILED: {step_message}")
                    return {
                        "success": False,
                        "error": step_message,
                        "failed_step": step_num,
                        "partial_results": self.execution_results,
                        "chain_data": self.chain_data
                    }
                
                logger.info(f"[STEP {step_num}] Status: {step_message}")
                
                # Store Step 1 as base for future inheritance
                if step_num == 1:
                    self.base_parameters = copy.deepcopy(params)
                    logger.info(f"Stored base parameters from Step 1: {len(params)} params")
                
                # Extract outputs for next steps
                if "output_mapping" in step_config:
                    logger.info(f"Extracting outputs with mapping: {step_config['output_mapping']}")
                    self._extract_outputs(result, step_config["output_mapping"])
                    logger.info(f"Chain data after extraction: {self.chain_data}")
                
                logger.info(f"[STEP {step_num}] Completed successfully")
            
            return {
                "success": True,
                "results": self.execution_results,
                "chain_data": self.chain_data
            }
        
        except Exception as e:
            logger.error(f"Chain execution failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "partial_results": self.execution_results,
                "chain_data": self.chain_data
            }
    
    def _build_parameters_with_inheritance(self, step_config: Dict, step_num: int) -> Dict:
        """
        Build parameters with inheritance:
        - Step 1: Use all params as-is, store as base
        - Step 2+: Always inherit from Step 1, override with step-specific params
        
        This allows Steps 2+ to reuse base parameters while changing task/tab specific fields.
        """
        params = {}
        
        # Step 1: Use provided params as-is
        if step_num == 1:
            params = step_config.get("parameters", {}).copy()
            logger.info(f"Step 1 params: {len(params)} parameters")
        else:
            # Step 2+: ALWAYS inherit from Step 1, then override with step config
            params = copy.deepcopy(self.base_parameters)
            step_overrides = step_config.get("parameters", {})
            params.update(step_overrides)
            
            logger.info(f"Step {step_num}:")
            logger.info(f"  Inherited {len(self.base_parameters)} from Step 1")
            logger.info(f"  Overridden {len(step_overrides)} with step-specific params")
            logger.info(f"  Final param count: {len(params)}")
            logger.debug(f"  Overrides applied: {list(step_overrides.keys())}")
        
        # Apply input mapping (injects values from chain_data)
        params = self._apply_input_mapping(params, step_config.get("input_mapping", {}))
        
        return params
    
    def _apply_input_mapping(self, params: Dict, input_mapping: Dict) -> Dict:
        """Replace parameter values with chain data from previous steps."""
        mapped_params = params.copy()
        
        if not input_mapping:
            return mapped_params
        
        logger.info(f"Applying input mappings: {input_mapping}")
        logger.info(f"Available chain_data: {self.chain_data}")
        
        for param_name, chain_var in input_mapping.items():
            if chain_var in self.chain_data:
                old_value = mapped_params.get(param_name)
                new_value = self.chain_data[chain_var]
                mapped_params[param_name] = new_value
                
                logger.info(f"  ✓ Mapped {param_name}: {old_value} → {new_value} (from chain_data['{chain_var}'])")
            else:
                logger.warning(f"  ⚠ Chain variable '{chain_var}' NOT FOUND in chain_data for {param_name}")
                logger.warning(f"    Available: {list(self.chain_data.keys())}")
        
        return mapped_params
    
    def _extract_outputs(self, result: Dict, output_mapping: Dict) -> None:
        """
        Extract output data and store in chain_data.
        For insert operations, extracts numeric ID from result row.
        """
        if not output_mapping:
            logger.debug("No output mappings specified")
            return
        
        logger.info(f"Extracting outputs: {output_mapping}")
        logger.debug(f"Result: {result}")
        
        # For result rows, find the new ID (usually last numeric column)
        if not result.get("rows") or len(result["rows"]) == 0:
            logger.warning(f"No rows in result")
            return
        
        first_row = result["rows"][0]
        logger.info(f"Extracting from first row: {first_row} (type={type(first_row).__name__})")
        
        # Convert to list/tuple for easier access (handles pyodbc Row objects)
        try:
            if hasattr(first_row, '__getitem__'):
                row_list = list(first_row)
            else:
                logger.warning(f"Cannot convert row to list: {first_row}")
                return
        except Exception as e:
            logger.warning(f"Error converting row: {e}")
            return
        
        logger.debug(f"Row as list: {row_list}")
        
        # Scan backwards to find the numeric ID (usually last number in row)
        for col_idx in range(len(row_list) - 1, -1, -1):
            cell_value = row_list[col_idx]
            cell_type = type(cell_value).__name__
            logger.debug(f"  Column {col_idx}: {cell_value} (type={cell_type})")
            
            # Check if numeric (int or float, but not bool)
            if isinstance(cell_value, (int, float)) and not isinstance(cell_value, bool) and cell_value > 0:
                # Found the ID, map it to chain_data
                for param_name, chain_var in output_mapping.items():
                    old_val = self.chain_data.get(chain_var)
                    self.chain_data[chain_var] = cell_value
                    logger.info(f"  ✓ Stored chain_data['{chain_var}'] = {cell_value} (was {old_val})")
                    return
        
        logger.warning(f"Could not extract numeric ID from row: {first_row}")
    
    def _check_step_status(self, result: Dict, step_num: int) -> tuple:
        """
        Check if a step succeeded or failed based on SP output.
        
        SP returns rows with format: (intStatus, strstatusschteam, intnewidschteam)
        - intStatus: 1=success, 0=failure
        - strstatusschteam: Message describing what happened
        - intnewidschteam: ID or other data
        
        Returns:
            (success: bool, message: str)
        """
        if not result.get("rows") or len(result["rows"]) == 0:
            logger.warning(f"[STEP {step_num}] No result rows returned")
            return (False, "No result rows returned from SP")
        
        first_row = result["rows"][0]
        
        # Convert to list for accessing columns
        try:
            row_list = list(first_row)
        except Exception as e:
            logger.error(f"[STEP {step_num}] Could not parse result row: {e}")
            return (False, f"Could not parse result row: {e}")
        
        if len(row_list) < 2:
            logger.error(f"[STEP {step_num}] Result row has insufficient columns: {row_list}")
            return (False, "Result row has insufficient columns")
        
        # Extract status and message
        int_status = row_list[0]  # Column 0: intStatus (1=success, 0=failure)
        str_message = row_list[1] if len(row_list) > 1 else ""  # Column 1: strstatusschteam
        
        # Convert to bool (anything != 0 is considered failure)
        is_success = bool(int_status) and int(int_status) != 0
        
        logger.debug(f"[STEP {step_num}] Status check: intStatus={int_status}, isSuccess={is_success}")
        logger.debug(f"[STEP {step_num}] Message: {str_message}")
        
        return (is_success, str_message)
    
    def _execute_sp(self, sp_name: str, params: Dict) -> Dict:
        """Execute single SP and capture outputs."""
        from core.db.procedures import run_stored_procedure
        
        result = run_stored_procedure(
            sp_name,
            params,
            capture_output_params=True
        )
        return result
