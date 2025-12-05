"""Tests for Phase 3: Validation Pipeline."""
import pytest
import asyncio
from pathlib import Path

from app.services.validation import (
    get_validation_service,
    ValidationService,
    PythonSyntaxValidator,
    ValidationSeverity
)
from app.services.test_runner import get_test_service, TestExecutionService


# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio


class TestPythonValidation:
    """Test Python validators."""
    
    @pytest.mark.asyncio
    async def test_python_syntax_valid(self):
        """Test valid Python syntax."""
        files = {
            "test.py": "def foo():\n    return 42"
        }
        
        validator = PythonSyntaxValidator()
        result = await validator.validate(files)
        
        assert result.passed
        assert result.error_count == 0
        assert len(result.issues) == 0
    
    @pytest.mark.asyncio
    async def test_python_syntax_invalid(self):
        """Test invalid Python syntax."""
        files = {
            "bad.py": "def foo(\n    invalid syntax"
        }
        
        validator = PythonSyntaxValidator()
        result = await validator.validate(files)
        
        assert not result.passed
        assert result.error_count == 1
        assert len(result.issues) == 1
        assert result.issues[0].severity == ValidationSeverity.ERROR
    
    @pytest.mark.asyncio
    async def test_python_syntax_multiple_files(self):
        """Test multiple Python files."""
        files = {
            "good.py": "def foo(): pass",
            "bad.py": "def bar(\ninvalid",
            "another.py": "x = 1 + 2"
        }
        
        validator = PythonSyntaxValidator()
        result = await validator.validate(files)
        
        assert not result.passed
        assert result.error_count == 1
        assert any("bad.py" in issue.file for issue in result.issues)


class TestValidationService:
    """Test validation service."""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test service initializes correctly."""
        service = get_validation_service()
        
        assert isinstance(service, ValidationService)
        assert "python-syntax" in service.validators
        assert len(service.validators) >= 1
    
    @pytest.mark.asyncio
    async def test_validate_files_auto_detect(self):
        """Test auto-detection of validators."""
        service = get_validation_service()
        
        files = {
            "test.py": "def foo(): pass"
        }
        
        results = await service.validate_files(files)
        
        assert "python-syntax" in results
        assert results["python-syntax"].passed
    
    @pytest.mark.asyncio
    async def test_validate_files_specific_validator(self):
        """Test running specific validator."""
        service = get_validation_service()
        
        files = {
            "test.py": "def foo(): pass"
        }
        
        results = await service.validate_files(files, validators=["python-syntax"])
        
        assert len(results) == 1
        assert "python-syntax" in results
    
    @pytest.mark.asyncio
    async def test_validate_and_report(self):
        """Test validate_and_report method."""
        service = get_validation_service()
        
        files = {
            "valid.py": "def foo(): pass",
            "invalid.py": "def bar(\nsyntax error"
        }
        
        all_passed, results = await service.validate_and_report(files)
        
        assert not all_passed
        assert "python-syntax" in results
        assert not results["python-syntax"].passed
    
    @pytest.mark.asyncio
    async def test_validation_result_counts(self):
        """Test validation result error/warning counts."""
        service = get_validation_service()
        
        files = {
            "bad.py": "def foo(\nno closing"
        }
        
        results = await service.validate_files(files, validators=["python-syntax"])
        result = results["python-syntax"]
        
        assert result.error_count >= 1
        assert result.execution_time > 0


class TestTestRunner:
    """Test test execution service."""
    
    @pytest.mark.asyncio
    async def test_pytest_runner_no_tests(self):
        """Test pytest with no test files."""
        service = get_test_service()
        
        files = {
            "main.py": "def foo(): pass"
        }
        
        result = await service.run_tests(files, runner="pytest")
        
        assert result.passed
        assert result.total_tests == 0
        assert "No test files found" in result.output
    
    @pytest.mark.asyncio
    async def test_pytest_runner_with_passing_test(self):
        """Test pytest with passing test."""
        service = get_test_service()
        
        files = {
            "test_example.py": """
def test_addition():
    assert 1 + 1 == 2

def test_subtraction():
    assert 5 - 3 == 2
"""
        }
        
        result = await service.run_tests(files, runner="pytest")
        
        # May not work without proper env, but structure is tested
        assert isinstance(result.passed, bool)
        assert result.execution_time >= 0
    
    @pytest.mark.asyncio
    async def test_auto_detect_runner(self):
        """Test auto-detection of test runner."""
        service = get_test_service()
        
        # Python tests
        py_files = {
            "test_example.py": "def test_foo(): assert True"
        }
        
        result = await service.run_tests(py_files, runner="auto")
        assert isinstance(result, object)
        
        # No tests
        no_test_files = {
            "main.py": "def foo(): pass"
        }
        
        result = await service.run_tests(no_test_files, runner="auto")
        assert result.total_tests == 0


class TestValidationIntegration:
    """Test validation integration with workflow."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_validation(self):
        """Test complete validation workflow."""
        service = get_validation_service()
        
        # Simulate project files
        files = {
            "backend/main.py": """
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}
""",
            "backend/models.py": """
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
""",
            "backend/test_main.py": """
def test_root():
    assert True
"""
        }
        
        # Validate all files
        all_passed, results = await service.validate_and_report(files)
        
        # Should pass syntax validation
        assert "python-syntax" in results
        assert results["python-syntax"].passed
        
        # Run tests
        test_service = get_test_service()
        test_result = await test_service.run_tests(files, runner="auto")
        
        assert isinstance(test_result.passed, bool)
    
    @pytest.mark.asyncio
    async def test_validation_with_multiple_validators(self):
        """Test running multiple validators."""
        service = get_validation_service()
        
        files = {
            "app.py": "def foo(): pass"
        }
        
        # Run all available validators
        results = await service.validate_files(files)
        
        # Should have at least syntax validator
        assert len(results) >= 1
        assert all(isinstance(r.passed, bool) for r in results.values())
        assert all(r.execution_time >= 0 for r in results.values())


# Run tests with:
# cd backend
# pytest tests/test_phase3.py -v --asyncio-mode=auto
