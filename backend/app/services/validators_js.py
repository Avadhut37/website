"""JavaScript/TypeScript validators."""
import tempfile
from pathlib import Path
from typing import Dict, List
import time
import json
import re

from .validation import BaseValidator, ValidationResult, ValidationIssue, ValidationSeverity
from ..core.logging import logger


class ESLintValidator(BaseValidator):
    """ESLint validator for JavaScript/TypeScript."""
    
    name = "eslint"
    file_patterns = ["*.js", "*.jsx", "*.ts", "*.tsx"]
    
    async def validate(self, files: Dict[str, str]) -> ValidationResult:
        """Run ESLint validation."""
        start_time = time.time()
        
        # Filter JS/TS files
        js_files = {f: c for f, c in files.items() if self.matches_file(f)}
        if not js_files:
            return ValidationResult(
                validator=self.name,
                passed=True,
                execution_time=time.time() - start_time
            )
        
        # Create temp directory with files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write files
            for filepath, content in js_files.items():
                file_path = tmppath / filepath
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
            
            # Create minimal eslintrc
            eslintrc = tmppath / ".eslintrc.json"
            eslintrc.write_text(json.dumps({
                "env": {
                    "browser": True,
                    "es2021": True,
                    "node": True
                },
                "extends": ["eslint:recommended"],
                "parserOptions": {
                    "ecmaVersion": 12,
                    "sourceType": "module",
                    "ecmaFeatures": {
                        "jsx": True
                    }
                },
                "rules": {}
            }), encoding="utf-8")
            
            # Run eslint
            cmd = [
                "npx", "eslint",
                "--format", "json",
                "--no-error-on-unmatched-pattern",
                str(tmppath)
            ]
            
            returncode, stdout, stderr = await self._run_command(cmd, tmppath, timeout=60)
            
            # Parse eslint JSON output
            issues = []
            try:
                if stdout:
                    results = json.loads(stdout)
                    for file_result in results:
                        if "messages" not in file_result:
                            continue
                        
                        rel_path = Path(file_result["filePath"]).relative_to(tmppath)
                        
                        for message in file_result["messages"]:
                            severity_map = {
                                2: ValidationSeverity.ERROR,
                                1: ValidationSeverity.WARNING,
                                0: ValidationSeverity.INFO
                            }
                            
                            issues.append(ValidationIssue(
                                file=str(rel_path),
                                line=message.get("line", 0),
                                column=message.get("column", 0),
                                severity=severity_map.get(message.get("severity", 1), ValidationSeverity.WARNING),
                                message=message.get("message", ""),
                                rule=message.get("ruleId", "unknown"),
                                fixable=message.get("fix") is not None
                            ))
            except json.JSONDecodeError:
                logger.warning(f"[ESLint] Failed to parse JSON output")
            except Exception as e:
                logger.error(f"[ESLint] Error parsing output: {e}")
            
            execution_time = time.time() - start_time
            
            return ValidationResult(
                validator=self.name,
                passed=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
                issues=issues,
                execution_time=execution_time
            )


class PrettierValidator(BaseValidator):
    """Prettier code formatter validator."""
    
    name = "prettier"
    file_patterns = ["*.js", "*.jsx", "*.ts", "*.tsx", "*.json", "*.css", "*.html"]
    
    async def validate(self, files: Dict[str, str]) -> ValidationResult:
        """Check if code is formatted with Prettier."""
        start_time = time.time()
        
        # Filter applicable files
        applicable_files = {f: c for f, c in files.items() if self.matches_file(f)}
        if not applicable_files:
            return ValidationResult(
                validator=self.name,
                passed=True,
                execution_time=time.time() - start_time
            )
        
        # Create temp directory with files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write files
            for filepath, content in applicable_files.items():
                file_path = tmppath / filepath
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
            
            # Run prettier in check mode
            cmd = [
                "npx", "prettier",
                "--check",
                "--log-level", "error",
                str(tmppath)
            ]
            
            returncode, stdout, stderr = await self._run_command(cmd, tmppath, timeout=60)
            
            # Prettier returns non-zero if files need formatting
            issues = []
            if returncode != 0:
                # Try to parse which files need formatting from stderr
                for filepath in applicable_files.keys():
                    issues.append(ValidationIssue(
                        file=filepath,
                        line=0,
                        column=0,
                        severity=ValidationSeverity.WARNING,
                        message="File would be reformatted by Prettier",
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


class TypeScriptValidator(BaseValidator):
    """TypeScript compiler validator."""
    
    name = "typescript"
    file_patterns = ["*.ts", "*.tsx"]
    
    async def validate(self, files: Dict[str, str]) -> ValidationResult:
        """Run TypeScript type checking."""
        start_time = time.time()
        
        # Filter TS files
        ts_files = {f: c for f, c in files.items() if self.matches_file(f)}
        if not ts_files:
            return ValidationResult(
                validator=self.name,
                passed=True,
                execution_time=time.time() - start_time
            )
        
        # Create temp directory with files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write files
            for filepath, content in ts_files.items():
                file_path = tmppath / filepath
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
            
            # Create minimal tsconfig.json
            tsconfig = tmppath / "tsconfig.json"
            tsconfig.write_text(json.dumps({
                "compilerOptions": {
                    "target": "ES2020",
                    "module": "ESNext",
                    "lib": ["ES2020", "DOM"],
                    "jsx": "react",
                    "strict": False,
                    "skipLibCheck": True,
                    "noEmit": True
                },
                "include": ["**/*"]
            }), encoding="utf-8")
            
            # Run tsc
            cmd = [
                "npx", "tsc",
                "--noEmit",
                "--pretty", "false"
            ]
            
            returncode, stdout, stderr = await self._run_command(cmd, tmppath, timeout=60)
            
            # Parse TypeScript compiler output
            issues = []
            # Format: path/file.ts(line,col): error TS1234: message
            pattern = r"^(.+?)\((\d+),(\d+)\): (error|warning) TS(\d+): (.+)$"
            
            output = stdout + stderr
            for line in output.splitlines():
                match = re.match(pattern, line)
                if match:
                    file, line_num, col, severity, code, message = match.groups()
                    try:
                        rel_path = Path(file).relative_to(tmppath)
                    except ValueError:
                        rel_path = Path(file)
                    
                    issues.append(ValidationIssue(
                        file=str(rel_path),
                        line=int(line_num),
                        column=int(col),
                        severity=ValidationSeverity.ERROR if severity == "error" else ValidationSeverity.WARNING,
                        message=message.strip(),
                        rule=f"TS{code}",
                        fixable=False
                    ))
            
            execution_time = time.time() - start_time
            
            return ValidationResult(
                validator=self.name,
                passed=returncode == 0,
                issues=issues,
                execution_time=execution_time
            )
