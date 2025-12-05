"""Validation service for code quality and correctness."""
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..core.logging import logger


class ValidationSeverity(str, Enum):
    """Validation issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""
    file: str
    line: int
    column: int
    severity: ValidationSeverity
    message: str
    rule: str
    fixable: bool = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "severity": self.severity.value,
            "message": self.message,
            "rule": self.rule,
            "fixable": self.fixable
        }


@dataclass
class ValidationResult:
    """Result of validation."""
    validator: str
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    execution_time: float = 0.0
    error: Optional[str] = None
    
    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "validator": self.validator,
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [issue.to_dict() for issue in self.issues],
            "execution_time": self.execution_time,
            "error": self.error
        }


class BaseValidator:
    """Base class for validators."""
    
    name: str = "base"
    file_patterns: List[str] = []  # e.g., ["*.py"]
    
    async def validate(self, files: Dict[str, str]) -> ValidationResult:
        """
        Validate files.
        
        Args:
            files: Dict of {filepath: content}
            
        Returns:
            ValidationResult
        """
        raise NotImplementedError
    
    def matches_file(self, filepath: str) -> bool:
        """Check if validator applies to file."""
        from fnmatch import fnmatch
        return any(fnmatch(filepath, pattern) for pattern in self.file_patterns)
    
    async def _run_command(
        self,
        cmd: List[str],
        cwd: Path,
        timeout: int = 30
    ) -> Tuple[int, str, str]:
        """
        Run a command asynchronously.
        
        Returns:
            (return_code, stdout, stderr)
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return (
                process.returncode or 0,
                stdout.decode("utf-8", errors="ignore"),
                stderr.decode("utf-8", errors="ignore")
            )
        except asyncio.TimeoutError:
            logger.error(f"[Validator] Command timeout: {' '.join(cmd)}")
            return (1, "", "Command timed out")
        except Exception as e:
            logger.error(f"[Validator] Command failed: {e}")
            return (1, "", str(e))


class PythonSyntaxValidator(BaseValidator):
    """Validate Python syntax."""
    
    name = "python-syntax"
    file_patterns = ["*.py"]
    
    async def validate(self, files: Dict[str, str]) -> ValidationResult:
        """Validate Python files for syntax errors."""
        import ast
        import time
        
        start_time = time.time()
        issues = []
        
        for filepath, content in files.items():
            if not self.matches_file(filepath):
                continue
            
            try:
                ast.parse(content)
            except SyntaxError as e:
                issues.append(ValidationIssue(
                    file=filepath,
                    line=e.lineno or 0,
                    column=e.offset or 0,
                    severity=ValidationSeverity.ERROR,
                    message=e.msg,
                    rule="syntax-error",
                    fixable=False
                ))
        
        execution_time = time.time() - start_time
        
        return ValidationResult(
            validator=self.name,
            passed=len(issues) == 0,
            issues=issues,
            execution_time=execution_time
        )


class MypyValidator(BaseValidator):
    """Mypy type checking validator."""
    
    name = "mypy"
    file_patterns = ["*.py"]
    
    async def validate(self, files: Dict[str, str]) -> ValidationResult:
        """Run mypy type checking."""
        import time
        import re
        
        start_time = time.time()
        
        # Filter Python files
        py_files = {f: c for f, c in files.items() if self.matches_file(f)}
        if not py_files:
            return ValidationResult(
                validator=self.name,
                passed=True,
                execution_time=time.time() - start_time
            )
        
        # Create temp directory with files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write files
            for filepath, content in py_files.items():
                file_path = tmppath / filepath
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
            
            # Run mypy
            cmd = [
                "mypy",
                "--ignore-missing-imports",
                "--no-error-summary",
                "--show-column-numbers",
                str(tmppath)
            ]
            
            returncode, stdout, stderr = await self._run_command(cmd, tmppath)
            
            # Parse mypy output
            issues = []
            # Format: path/file.py:line:col: error: message
            pattern = r"^(.+?):(\d+):(\d+): (error|warning|note): (.+)$"
            
            for line in stdout.splitlines():
                match = re.match(pattern, line)
                if match:
                    file, line_num, col, severity, message = match.groups()
                    # Make path relative
                    rel_path = Path(file).relative_to(tmppath)
                    
                    issues.append(ValidationIssue(
                        file=str(rel_path),
                        line=int(line_num),
                        column=int(col),
                        severity=ValidationSeverity.ERROR if severity == "error" else ValidationSeverity.WARNING,
                        message=message.strip(),
                        rule="type-check",
                        fixable=False
                    ))
            
            execution_time = time.time() - start_time
            
            return ValidationResult(
                validator=self.name,
                passed=returncode == 0 and len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
                issues=issues,
                execution_time=execution_time
            )


class BanditValidator(BaseValidator):
    """Bandit security validator."""
    
    name = "bandit"
    file_patterns = ["*.py"]
    
    async def validate(self, files: Dict[str, str]) -> ValidationResult:
        """Run bandit security checks."""
        import time
        import json
        
        start_time = time.time()
        
        # Filter Python files
        py_files = {f: c for f, c in files.items() if self.matches_file(f)}
        if not py_files:
            return ValidationResult(
                validator=self.name,
                passed=True,
                execution_time=time.time() - start_time
            )
        
        # Create temp directory with files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write files
            for filepath, content in py_files.items():
                file_path = tmppath / filepath
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
            
            # Run bandit
            cmd = [
                "bandit",
                "-r", str(tmppath),
                "-f", "json",
                "-q"  # Quiet mode
            ]
            
            returncode, stdout, stderr = await self._run_command(cmd, tmppath)
            
            # Parse bandit JSON output
            issues = []
            try:
                if stdout:
                    result = json.loads(stdout)
                    for finding in result.get("results", []):
                        rel_path = Path(finding["filename"]).relative_to(tmppath)
                        
                        # Map bandit severity to our severity
                        severity_map = {
                            "HIGH": ValidationSeverity.ERROR,
                            "MEDIUM": ValidationSeverity.WARNING,
                            "LOW": ValidationSeverity.INFO
                        }
                        
                        issues.append(ValidationIssue(
                            file=str(rel_path),
                            line=finding["line_number"],
                            column=0,
                            severity=severity_map.get(finding["issue_severity"], ValidationSeverity.WARNING),
                            message=finding["issue_text"],
                            rule=finding["test_id"],
                            fixable=False
                        ))
            except json.JSONDecodeError:
                logger.warning(f"[Bandit] Failed to parse JSON output")
            
            execution_time = time.time() - start_time
            
            return ValidationResult(
                validator=self.name,
                passed=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
                issues=issues,
                execution_time=execution_time
            )


class BlackValidator(BaseValidator):
    """Black code formatter validator."""
    
    name = "black"
    file_patterns = ["*.py"]
    
    async def validate(self, files: Dict[str, str]) -> ValidationResult:
        """Check if Python code is formatted with black."""
        import time
        
        start_time = time.time()
        
        # Filter Python files
        py_files = {f: c for f, c in files.items() if self.matches_file(f)}
        if not py_files:
            return ValidationResult(
                validator=self.name,
                passed=True,
                execution_time=time.time() - start_time
            )
        
        # Create temp directory with files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write files
            for filepath, content in py_files.items():
                file_path = tmppath / filepath
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
            
            # Run black in check mode
            cmd = [
                "black",
                "--check",
                "--quiet",
                str(tmppath)
            ]
            
            returncode, stdout, stderr = await self._run_command(cmd, tmppath)
            
            # Black returns 1 if files would be reformatted
            issues = []
            if returncode != 0:
                # Parse which files need formatting
                for filepath in py_files.keys():
                    issues.append(ValidationIssue(
                        file=filepath,
                        line=0,
                        column=0,
                        severity=ValidationSeverity.WARNING,
                        message="File would be reformatted by black",
                        rule="format",
                        fixable=True
                    ))
            
            execution_time = time.time() - start_time
            
            return ValidationResult(
                validator=self.name,
                passed=returncode == 0,
                issues=issues,
                execution_time=execution_time
            )


class ValidationService:
    """Service for validating code quality."""
    
    def __init__(self):
        self.validators: Dict[str, BaseValidator] = {}
        self._register_default_validators()
    
    def _register_default_validators(self):
        """Register default validators."""
        self.register_validator(PythonSyntaxValidator())
        
        # Optional validators (require external tools)
        try:
            import mypy
            self.register_validator(MypyValidator())
        except ImportError:
            logger.info("[Validation] mypy not available")
        
        # Check if bandit is available
        try:
            subprocess.run(["bandit", "--version"], capture_output=True, check=True)
            self.register_validator(BanditValidator())
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.info("[Validation] bandit not available")
        
        # Check if black is available
        try:
            subprocess.run(["black", "--version"], capture_output=True, check=True)
            self.register_validator(BlackValidator())
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.info("[Validation] black not available")
    
    def register_validator(self, validator: BaseValidator):
        """Register a validator."""
        self.validators[validator.name] = validator
        logger.info(f"[Validation] Registered validator: {validator.name}")
    
    async def validate_files(
        self,
        files: Dict[str, str],
        validators: Optional[List[str]] = None
    ) -> Dict[str, ValidationResult]:
        """
        Validate files with specified validators.
        
        Args:
            files: Dict of {filepath: content}
            validators: List of validator names (None = all applicable)
            
        Returns:
            Dict of {validator_name: ValidationResult}
        """
        # Determine which validators to run
        if validators:
            active_validators = [
                self.validators[name]
                for name in validators
                if name in self.validators
            ]
        else:
            # Auto-detect based on file patterns
            active_validators = []
            for validator in self.validators.values():
                if any(validator.matches_file(f) for f in files.keys()):
                    active_validators.append(validator)
        
        if not active_validators:
            logger.info("[Validation] No applicable validators found")
            return {}
        
        logger.info(f"[Validation] Running {len(active_validators)} validators")
        
        # Run validators in parallel
        tasks = [validator.validate(files) for validator in active_validators]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        validation_results = {}
        for validator, result in zip(active_validators, results):
            if isinstance(result, Exception):
                logger.error(f"[Validation] {validator.name} failed: {result}")
                validation_results[validator.name] = ValidationResult(
                    validator=validator.name,
                    passed=False,
                    error=str(result)
                )
            else:
                validation_results[validator.name] = result
        
        return validation_results
    
    async def validate_and_report(
        self,
        files: Dict[str, str],
        validators: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, ValidationResult]]:
        """
        Validate files and return pass/fail status.
        
        Returns:
            (all_passed, results_dict)
        """
        results = await self.validate_files(files, validators)
        
        # Check if all passed
        all_passed = all(r.passed for r in results.values())
        
        # Log summary
        total_errors = sum(r.error_count for r in results.values())
        total_warnings = sum(r.warning_count for r in results.values())
        
        logger.info(
            f"[Validation] Complete: "
            f"{'✅ PASSED' if all_passed else '❌ FAILED'} "
            f"({total_errors} errors, {total_warnings} warnings)"
        )
        
        return all_passed, results


# Global validation service instance
_validation_service: Optional[ValidationService] = None


def get_validation_service() -> ValidationService:
    """Get or create validation service."""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service
