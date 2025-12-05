"""AST-aware code patching for minimal diffs."""
import ast
import json
import difflib
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass

from ..core.logging import logger


@dataclass
class CodePatch:
    """Represents a code patch."""
    file_path: str
    patch_type: str  # 'full_replace', 'function_add', 'function_replace', 'import_add'
    target: Optional[str] = None  # function/class name
    content: str = ""
    line_number: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "patch_type": self.patch_type,
            "target": self.target,
            "content": self.content,
            "line_number": self.line_number
        }


class PythonASTPatcher:
    """AST-aware patching for Python files."""
    
    @staticmethod
    def analyze_changes(old_code: str, new_code: str) -> Tuple[bool, str, List[str]]:
        """
        Analyze changes between old and new code.
        
        Returns:
            (can_patch, reason, changes_list)
        """
        try:
            old_ast = ast.parse(old_code)
            new_ast = ast.parse(new_code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}", []
        
        # Get all top-level definitions
        old_defs = PythonASTPatcher._get_definitions(old_ast)
        new_defs = PythonASTPatcher._get_definitions(new_ast)
        
        changes = []
        
        # Check for additions
        for name in new_defs.keys() - old_defs.keys():
            changes.append(f"Added {new_defs[name]['type']} '{name}'")
        
        # Check for deletions
        for name in old_defs.keys() - new_defs.keys():
            changes.append(f"Deleted {old_defs[name]['type']} '{name}'")
        
        # Check for modifications
        for name in old_defs.keys() & new_defs.keys():
            old_src = ast.get_source_segment(old_code, old_defs[name]['node'])
            new_src = ast.get_source_segment(new_code, new_defs[name]['node'])
            if old_src != new_src:
                changes.append(f"Modified {old_defs[name]['type']} '{name}'")
        
        can_patch = len(changes) <= 5  # Reasonable threshold
        reason = f"{len(changes)} changes detected" if changes else "No changes"
        
        return can_patch, reason, changes
    
    @staticmethod
    def _get_definitions(tree: ast.AST) -> Dict:
        """Extract all top-level function and class definitions."""
        defs = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                # Only get top-level definitions
                if isinstance(node, ast.FunctionDef):
                    defs[node.name] = {'type': 'function', 'node': node}
                else:
                    defs[node.name] = {'type': 'class', 'node': node}
                break  # Don't recurse into nested functions/classes
        return defs
    
    @staticmethod
    def generate_patch(old_code: str, new_code: str, file_path: str) -> Optional[CodePatch]:
        """Generate a minimal patch for Python code."""
        can_patch, reason, changes = PythonASTPatcher.analyze_changes(old_code, new_code)
        
        if not can_patch or not changes:
            # Fall back to full replacement
            logger.debug(f"[ASTPatcher] Using full replacement for {file_path}: {reason}")
            return CodePatch(
                file_path=file_path,
                patch_type="full_replace",
                content=new_code
            )
        
        try:
            old_ast = ast.parse(old_code)
            new_ast = ast.parse(new_code)
            
            old_defs = PythonASTPatcher._get_definitions(old_ast)
            new_defs = PythonASTPatcher._get_definitions(new_ast)
            
            # Find the first significant change
            for name in new_defs.keys() - old_defs.keys():
                # New definition added
                node = new_defs[name]['node']
                content = ast.get_source_segment(new_code, node)
                return CodePatch(
                    file_path=file_path,
                    patch_type="function_add" if new_defs[name]['type'] == 'function' else "class_add",
                    target=name,
                    content=content,
                    line_number=node.lineno
                )
            
            for name in old_defs.keys() & new_defs.keys():
                # Modified definition
                old_src = ast.get_source_segment(old_code, old_defs[name]['node'])
                new_src = ast.get_source_segment(new_code, new_defs[name]['node'])
                if old_src != new_src:
                    return CodePatch(
                        file_path=file_path,
                        patch_type="function_replace" if new_defs[name]['type'] == 'function' else "class_replace",
                        target=name,
                        content=new_src,
                        line_number=new_defs[name]['node'].lineno
                    )
            
        except Exception as e:
            logger.error(f"[ASTPatcher] Patch generation failed: {e}")
        
        # Fallback to full replacement
        return CodePatch(
            file_path=file_path,
            patch_type="full_replace",
            content=new_code
        )
    
    @staticmethod
    def apply_patch(old_code: str, patch: CodePatch) -> str:
        """Apply a patch to Python code."""
        if patch.patch_type == "full_replace":
            return patch.content
        
        if patch.patch_type in ["function_add", "class_add"]:
            # Append to end of file
            return old_code.rstrip() + "\n\n\n" + patch.content
        
        if patch.patch_type in ["function_replace", "class_replace"]:
            # Try to replace the specific function/class
            try:
                old_ast = ast.parse(old_code)
                lines = old_code.splitlines(keepends=True)
                
                # Find the target definition
                for node in ast.walk(old_ast):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        if node.name == patch.target:
                            # Replace lines
                            start_line = node.lineno - 1
                            end_line = node.end_lineno
                            
                            new_lines = (
                                lines[:start_line] +
                                [patch.content + "\n"] +
                                lines[end_line:]
                            )
                            return ''.join(new_lines)
            
            except Exception as e:
                logger.error(f"[ASTPatcher] Apply patch failed: {e}")
        
        # Fallback to full replacement
        return patch.content


class UnifiedDiffGenerator:
    """Generate unified diffs (git-style)."""
    
    @staticmethod
    def generate(old_content: str, new_content: str, file_path: str) -> str:
        """Generate a unified diff."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=""
        )
        
        return ''.join(diff)
    
    @staticmethod
    def apply(original: str, diff: str) -> Optional[str]:
        """Apply a unified diff (basic implementation)."""
        # This is a simplified implementation
        # For production, consider using a library like `patch` or `unidiff`
        lines = original.splitlines(keepends=True)
        
        # Parse diff (very basic)
        # In production, use proper diff parsing
        logger.warning("[DiffGenerator] Apply diff not fully implemented")
        return None


class JavaScriptPatcher:
    """AST-aware patching for JavaScript/JSX files."""
    
    @staticmethod
    def generate_patch(old_code: str, new_code: str, file_path: str) -> CodePatch:
        """Generate a patch for JavaScript code."""
        # For Phase 2, we'll use full replacement
        # Phase 3 can add Babel/Acorn for JS AST parsing
        
        logger.debug(f"[JSPatcher] Using full replacement for {file_path}")
        return CodePatch(
            file_path=file_path,
            patch_type="full_replace",
            content=new_code
        )
    
    @staticmethod
    def apply_patch(old_code: str, patch: CodePatch) -> str:
        """Apply a patch to JavaScript code."""
        return patch.content


def generate_patch(old_code: str, new_code: str, file_path: str) -> CodePatch:
    """
    Generate a patch for any supported file type.
    
    Args:
        old_code: Original file content
        new_code: New file content
        file_path: File path (determines language)
        
    Returns:
        CodePatch object
    """
    if file_path.endswith('.py'):
        return PythonASTPatcher.generate_patch(old_code, new_code, file_path)
    elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
        return JavaScriptPatcher.generate_patch(old_code, new_code, file_path)
    else:
        # Default to full replacement
        return CodePatch(
            file_path=file_path,
            patch_type="full_replace",
            content=new_code
        )


def apply_patch(old_code: str, patch: CodePatch) -> str:
    """
    Apply a patch to code.
    
    Args:
        old_code: Original code
        patch: CodePatch to apply
        
    Returns:
        Patched code
    """
    if patch.file_path.endswith('.py'):
        return PythonASTPatcher.apply_patch(old_code, patch)
    elif patch.file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
        return JavaScriptPatcher.apply_patch(old_code, patch)
    else:
        return patch.content
