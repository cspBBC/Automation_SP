"""Test Orchestrator - Coordinates complete test execution flow."""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

from .builder import ConfigLoader, TestCaseBuilder
from .runner import run_stored_procedures
from .utils import setup_logging


class TestResults:
    """Aggregates test execution results and metrics."""
    
    def __init__(self):
        """Initialize results container."""
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        self.test_results: List[Dict[str, Any]] = []
        self.start_time = None
        self.end_time = None
        self.errors: List[str] = []
    
    def add_result(self, test_id: str, status: str, result: Dict = None, error: str = None):
        """Add a test result.
        
        Args:
            test_id: Test identifier
            status: Test status ('passed', 'failed', 'skipped', 'error')
            result: Test result data
            error: Error message if applicable
        """
        self.test_results.append({
            'test_id': test_id,
            'status': status,
            'result': result or {},
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        
        if status == 'passed':
            self.passed_tests += 1
        elif status == 'failed':
            self.failed_tests += 1
        elif status == 'skipped':
            self.skipped_tests += 1
        
        self.total_tests += 1
        
        if error and status != 'skipped':
            self.errors.append(f"{test_id}: {error}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test results summary.
        
        Returns:
            Dictionary with summary metrics
        """
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        pass_rate = 0
        if self.total_tests > 0:
            pass_rate = round((self.passed_tests / self.total_tests) * 100, 2)
        
        return {
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'skipped_tests': self.skipped_tests,
            'pass_rate': pass_rate,
            'duration_seconds': duration,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_count': len(self.errors),
            'errors': self.errors[:10]  # First 10 errors
        }
    
    def print_summary(self):
        """Print results summary to console."""
        summary = self.get_summary()
        print("\n" + "="*60)
        print("TEST EXECUTION SUMMARY")
        print("="*60)
        print(f"Total Tests:    {summary['total_tests']}")
        print(f"Passed:         {summary['passed_tests']}")
        print(f"Failed:         {summary['failed_tests']}")
        print(f"Skipped:        {summary['skipped_tests']}")
        print(f"Pass Rate:      {summary['pass_rate']}%")
        if summary['duration_seconds']:
            print(f"Duration:       {summary['duration_seconds']:.2f}s")
        if summary['errors']:
            print(f"\nErrors ({len(summary['errors'])}):")
            for error in summary['errors'][:5]:
                print(f"  - {error}")
        print("="*60 + "\n")


class TestOrchestrator:
    """Orchestrates the complete test execution flow per PowerPoint architecture.
    
    Test Execution Flow:
    1. Load Configuration
    2. Load Test Data
    3. Build Test Cases
    4. Connect to Database
    5. Execute Tests
    6. Aggregate Results
    """
    
    def __init__(self, config_path: str = None, log_level: str = 'INFO'):
        """Initialize TestOrchestrator.
        
        Args:
            config_path: Path to YAML configuration file
            log_level: Logging level
        """
        self.logger = setup_logging('TestOrchestrator', log_level)
        self.config_path = config_path
        self.config = {}
        self.test_builder = TestCaseBuilder()
        self.results = TestResults()
    
    def step_1_load_configuration(self) -> bool:
        """Step 1: Load Configuration from YAML.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Step 1: Loading Configuration...")
            
            if not self.config_path:
                self.logger.warning("No config file specified, using defaults")
                self.config = self._get_default_config()
            else:
                self.config = ConfigLoader.load_config(self.config_path)
                self.logger.info(f"Configuration loaded from {self.config_path}")
            
            self.logger.info("✓ Configuration loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Failed to load configuration: {e}")
            self.results.errors.append(f"Config load failed: {e}")
            return False
    
    def step_2_load_test_data(self, data_source: str = None) -> List[Dict]:
        """Step 2: Load Test Data from files.
        
        Args:
            data_source: Path to test data file (overrides config)
            
        Returns:
            List of test data dictionaries
        """
        try:
            self.logger.info("Step 2: Loading Test Data...")
            
            if data_source is None:
                data_source = self.config.get('test', {}).get('data_source', None)
            
            if not data_source:
                self.logger.error("No data source specified")
                return []
            
            test_data = self.test_builder.build_from_file(data_source)
            self.logger.info(f"✓ Loaded {len(test_data)} test cases from {data_source}")
            return test_data
            
        except Exception as e:
            self.logger.error(f"✗ Failed to load test data: {e}")
            self.results.errors.append(f"Data load failed: {e}")
            return []
    
    def step_3_build_test_cases(self, test_data: List[Dict]) -> List[Dict]:
        """Step 3: Build and Validate Test Cases.
        
        Args:
            test_data: List of raw test data dictionaries
            
        Returns:
            List of validated test case objects
        """
        try:
            self.logger.info("Step 3: Building Test Cases...")
            
            test_cases = self.test_builder.create_test_objects(test_data)
            self.logger.info(f"✓ Built {len(test_cases)} test cases")
            return test_cases
            
        except Exception as e:
            self.logger.error(f"✗ Failed to build test cases: {e}")
            self.results.errors.append(f"Test case build failed: {e}")
            return []
    
    def step_4_connect_database(self) -> bool:
        """Step 4: Verify Database Connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info("Step 4: Verifying Database Connection...")
            
            from database_layer.connection import DBSession
            with DBSession() as db:
                # Test connection with simple query
                results = db.execute_query("SELECT @@VERSION")
                if results:
                    self.logger.info(f"✓ Database connection verified")
                    return True
                else:
                    self.logger.error("Database connection test returned no results")
                    return False
                    
        except Exception as e:
            self.logger.error(f"✗ Failed to connect to database: {e}")
            self.results.errors.append(f"Database connection failed: {e}")
            return False
    
    def step_5_execute_tests(self, test_cases: List[Dict]) -> List[Dict]:
        """Step 5: Execute all test cases.
        
        Args:
            test_cases: List of test case objects to execute
            
        Returns:
            List of test results
        """
        try:
            self.logger.info(f"Step 5: Executing {len(test_cases)} Tests...")
            self.results.start_time = datetime.now()
            
            all_results = []
            for i, test_case in enumerate(test_cases, 1):
                try:
                    self.logger.info(f"  Executing test {i}/{len(test_cases)}: {test_case.get('id', 'unknown')}")
                    
                    # Execute stored procedure(s)
                    result = run_stored_procedures(
                        stored_procedure=test_case.get('stored_procedure'),
                        parameters=test_case.get('input', {}),
                        chain_procedures=test_case.get('chain_procedures', []),
                        timeout=self.config.get('test', {}).get('timeout', 30)
                    )
                    
                    # Add result with validation status
                    all_results.append(result)
                    self.results.add_result(
                        test_case.get('id', 'unknown'),
                        'passed',
                        result
                    )
                    self.logger.info(f"    ✓ Test passed")
                    
                except Exception as e:
                    self.logger.error(f"    ✗ Test failed: {e}")
                    self.results.add_result(
                        test_case.get('id', 'unknown'),
                        'failed',
                        error=str(e)
                    )
                    all_results.append({'error': str(e)})
            
            self.results.end_time = datetime.now()
            self.logger.info(f"✓ Test execution completed")
            return all_results
            
        except Exception as e:
            self.logger.error(f"✗ Test execution failed: {e}")
            self.results.errors.append(f"Test execution failed: {e}")
            self.results.end_time = datetime.now()
            return []
    
    def step_6_aggregate_results(self, test_results: List[Dict]) -> Dict[str, Any]:
        """Step 6: Aggregate and summarize test results.
        
        Args:
            test_results: List of test result dictionaries
            
        Returns:
            Aggregated results summary
        """
        try:
            self.logger.info("Step 6: Aggregating Results...")
            
            summary = self.results.get_summary()
            self.logger.info("✓ Results aggregated")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"✗ Failed to aggregate results: {e}")
            return {}
    
    def run_tests(self, data_source: str = None) -> Dict[str, Any]:
        """Run complete test execution flow.
        
        Args:
            data_source: Path to test data file
            
        Returns:
            Test results summary dictionary
        """
        self.logger.info("="*60)
        self.logger.info("STARTING TEST ORCHESTRATION")
        self.logger.info("="*60)
        
        # Step 1: Load Configuration
        if not self.step_1_load_configuration():
            return self.results.get_summary()
        
        # Step 2: Load Test Data
        test_data = self.step_2_load_test_data(data_source)
        if not test_data:
            return self.results.get_summary()
        
        # Step 3: Build Test Cases
        test_cases = self.step_3_build_test_cases(test_data)
        if not test_cases:
            return self.results.get_summary()
        
        # Step 4: Connect to Database
        if not self.step_4_connect_database():
            return self.results.get_summary()
        
        # Step 5: Execute Tests
        test_results = self.step_5_execute_tests(test_cases)
        
        # Step 6: Aggregate Results
        summary = self.step_6_aggregate_results(test_results)
        
        self.logger.info("="*60)
        self.logger.info("TEST ORCHESTRATION COMPLETED")
        self.logger.info("="*60)
        
        # Print visual summary
        self.results.print_summary()
        
        return summary
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'database': {
                'timeout': 30,
                'isolation_level': 'READ_COMMITTED'
            },
            'test': {
                'timeout': 30,
                'retry_count': 0,
                'data_source': 'data_layer/test_data/createSchdGroup_testData.json'
            }
        }
