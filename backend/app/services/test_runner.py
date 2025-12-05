"""Test execution service for dynamic validation."""
import asyncio
import tempfile
import json
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
import time

from ..core.logging import logger


@dataclass
class TestResult:
    """Result of test execution."""
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    execution_time: float
    output: str
    coverage: Optional[Dict] = None
    errors: List[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "execution_time": self.execution_time,
            "output": self.output,
            "coverage": self.coverage,
            "errors": self.errors or []
        }


class TestRunner:
    """Base class for test runners."""
    
    name: str = "base"
    
    async def run_tests(
        self,
        files: Dict[str, str],
        with_coverage: bool = False
    ) -> TestResult:
        """Run tests on files."""
        raise NotImplementedError


class PytestRunner(TestRunner):
    """Pytest test runner."""
    
    name = "pytest"
    
    async def run_tests(
        self,
        files: Dict[str, str],
        with_coverage: bool = False
    ) -> TestResult:
        """Run pytest on Python test files."""
        start_time = time.time()
        
        # Filter test files
        test_files = {
            f: c for f, c in files.items()
            if f.startswith("test_") or f.endswith("_test.py") or "/tests/" in f
        }
        
        if not test_files:
            return TestResult(
                passed=True,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                execution_time=time.time() - start_time,
                output="No test files found"
            )
        
        # Create temp directory with all files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write all files (tests + dependencies)
            for filepath, content in files.items():
                file_path = tmppath / filepath
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
            
            # Build pytest command
            cmd = ["python", "-m", "pytest", "-v", "--tb=short"]
            
            if with_coverage:
                cmd.extend(["--cov=.", "--cov-report=json"])
            
            # Add test files
            for test_file in test_files.keys():
                cmd.append(str(tmppath / test_file))
            
            # Run pytest
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=tmppath,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=120  # 2 minute timeout
                )
                
                output = stdout.decode("utf-8", errors="ignore")
                error_output = stderr.decode("utf-8", errors="ignore")
                
                # Parse pytest output
                total_tests = 0
                passed_tests = 0
                failed_tests = 0
                skipped_tests = 0
                
                # Look for summary line: "X passed, Y failed, Z skipped"
                import re
                summary_pattern = r"(\d+) passed|(\d+) failed|(\d+) skipped"
                matches = re.findall(summary_pattern, output)
                
                for match in matches:
                    if match[0]:  # passed
                        passed_tests = int(match[0])
                    if match[1]:  # failed
                        failed_tests = int(match[1])
                    if match[2]:  # skipped
                        skipped_tests = int(match[2])
                
                total_tests = passed_tests + failed_tests + skipped_tests
                
                # Load coverage if requested
                coverage_data = None
                if with_coverage:
                    coverage_file = tmppath / "coverage.json"
                    if coverage_file.exists():
                        try:
                            coverage_data = json.loads(coverage_file.read_text())
                        except Exception as e:
                            logger.warning(f"[Pytest] Failed to load coverage: {e}")
                
                execution_time = time.time() - start_time
                
                return TestResult(
                    passed=process.returncode == 0,
                    total_tests=total_tests,
                    passed_tests=passed_tests,
                    failed_tests=failed_tests,
                    skipped_tests=skipped_tests,
                    execution_time=execution_time,
                    output=output + "\n" + error_output,
                    coverage=coverage_data
                )
                
            except asyncio.TimeoutError:
                return TestResult(
                    passed=False,
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=0,
                    skipped_tests=0,
                    execution_time=time.time() - start_time,
                    output="Test execution timed out",
                    errors=["Timeout after 120 seconds"]
                )
            except Exception as e:
                logger.error(f"[Pytest] Test execution failed: {e}")
                return TestResult(
                    passed=False,
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=0,
                    skipped_tests=0,
                    execution_time=time.time() - start_time,
                    output=str(e),
                    errors=[str(e)]
                )


class JestRunner(TestRunner):
    """Jest test runner for JavaScript/TypeScript."""
    
    name = "jest"
    
    async def run_tests(
        self,
        files: Dict[str, str],
        with_coverage: bool = False
    ) -> TestResult:
        """Run Jest on JavaScript test files."""
        start_time = time.time()
        
        # Filter test files
        test_files = {
            f: c for f, c in files.items()
            if any(pattern in f for pattern in [".test.", ".spec.", "__tests__/"])
        }
        
        if not test_files:
            return TestResult(
                passed=True,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                execution_time=time.time() - start_time,
                output="No test files found"
            )
        
        # Create temp directory with all files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write all files
            for filepath, content in files.items():
                file_path = tmppath / filepath
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
            
            # Create minimal package.json
            package_json = tmppath / "package.json"
            package_json.write_text(json.dumps({
                "name": "test-project",
                "version": "1.0.0",
                "scripts": {
                    "test": "jest"
                }
            }), encoding="utf-8")
            
            # Build jest command
            cmd = ["npx", "jest", "--json", "--verbose"]
            
            if with_coverage:
                cmd.append("--coverage")
            
            # Run jest
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=tmppath,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=120
                )
                
                output = stdout.decode("utf-8", errors="ignore")
                
                # Parse Jest JSON output
                try:
                    result = json.loads(output)
                    
                    total_tests = result.get("numTotalTests", 0)
                    passed_tests = result.get("numPassedTests", 0)
                    failed_tests = result.get("numFailedTests", 0)
                    skipped_tests = result.get("numPendingTests", 0)
                    
                    coverage_data = result.get("coverageMap") if with_coverage else None
                    
                    return TestResult(
                        passed=result.get("success", False),
                        total_tests=total_tests,
                        passed_tests=passed_tests,
                        failed_tests=failed_tests,
                        skipped_tests=skipped_tests,
                        execution_time=time.time() - start_time,
                        output=json.dumps(result, indent=2),
                        coverage=coverage_data
                    )
                    
                except json.JSONDecodeError:
                    # Fallback to text output
                    return TestResult(
                        passed=process.returncode == 0,
                        total_tests=0,
                        passed_tests=0,
                        failed_tests=0,
                        skipped_tests=0,
                        execution_time=time.time() - start_time,
                        output=output
                    )
                    
            except asyncio.TimeoutError:
                return TestResult(
                    passed=False,
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=0,
                    skipped_tests=0,
                    execution_time=time.time() - start_time,
                    output="Test execution timed out",
                    errors=["Timeout after 120 seconds"]
                )
            except Exception as e:
                logger.error(f"[Jest] Test execution failed: {e}")
                return TestResult(
                    passed=False,
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=0,
                    skipped_tests=0,
                    execution_time=time.time() - start_time,
                    output=str(e),
                    errors=[str(e)]
                )


class TestExecutionService:
    """Service for executing tests."""
    
    def __init__(self):
        self.runners: Dict[str, TestRunner] = {
            "pytest": PytestRunner(),
            "jest": JestRunner()
        }
    
    async def run_tests(
        self,
        files: Dict[str, str],
        runner: str = "auto",
        with_coverage: bool = False
    ) -> TestResult:
        """
        Run tests on files.
        
        Args:
            files: Dict of {filepath: content}
            runner: "pytest", "jest", or "auto" (auto-detect)
            with_coverage: Include coverage data
            
        Returns:
            TestResult
        """
        # Auto-detect runner
        if runner == "auto":
            has_py_tests = any(
                f.endswith(".py") and ("test_" in f or "_test.py" in f or "/tests/" in f)
                for f in files.keys()
            )
            has_js_tests = any(
                any(pattern in f for pattern in [".test.", ".spec.", "__tests__/"])
                for f in files.keys()
            )
            
            if has_py_tests:
                runner = "pytest"
            elif has_js_tests:
                runner = "jest"
            else:
                logger.info("[TestExecution] No test files detected")
                return TestResult(
                    passed=True,
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=0,
                    skipped_tests=0,
                    execution_time=0.0,
                    output="No test files found"
                )
        
        # Get runner
        test_runner = self.runners.get(runner)
        if not test_runner:
            raise ValueError(f"Unknown test runner: {runner}")
        
        logger.info(f"[TestExecution] Running tests with {runner}")
        result = await test_runner.run_tests(files, with_coverage)
        
        logger.info(
            f"[TestExecution] {runner} complete: "
            f"{'✅ PASSED' if result.passed else '❌ FAILED'} "
            f"({result.passed_tests}/{result.total_tests} passed)"
        )
        
        return result


# Global test execution service
_test_service: Optional[TestExecutionService] = None


def get_test_service() -> TestExecutionService:
    """Get or create test execution service."""
    global _test_service
    if _test_service is None:
        _test_service = TestExecutionService()
    return _test_service
