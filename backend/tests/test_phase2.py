"""Tests for Phase 2: VFS + AST Patching."""
import pytest
from pathlib import Path
import tempfile
import shutil

from app.services.vfs import VirtualFileSystem, FileStatus, get_vfs, clear_vfs
from app.services.ast_patcher import (
    PythonASTPatcher, 
    CodePatch, 
    generate_patch, 
    apply_patch
)


class TestVirtualFileSystem:
    """Test VFS functionality."""
    
    def setup_method(self):
        """Setup test VFS."""
        self.vfs = VirtualFileSystem(project_id=999)
    
    def test_write_and_read_file(self):
        """Test basic file operations."""
        self.vfs.write_file("test.py", "print('hello')")
        content = self.vfs.read_file("test.py")
        
        assert content == "print('hello')"
    
    def test_file_status_tracking(self):
        """Test file status changes."""
        # New file
        self.vfs.write_file("new.py", "# new file")
        assert self.vfs.files["new.py"].status == FileStatus.ADDED
        
        # Commit makes it unchanged
        self.vfs.commit("Add new.py")
        assert self.vfs.files["new.py"].status == FileStatus.UNCHANGED
        
        # Modify file
        self.vfs.write_file("new.py", "# modified")
        assert self.vfs.files["new.py"].status == FileStatus.MODIFIED
    
    def test_commit_and_rollback(self):
        """Test commit and rollback functionality."""
        # Add files
        self.vfs.write_file("file1.py", "version 1")
        commit1 = self.vfs.commit("First commit")
        
        # Modify
        self.vfs.write_file("file1.py", "version 2")
        commit2 = self.vfs.commit("Second commit")
        
        # Rollback to first commit
        success = self.vfs.rollback(commit1)
        assert success
        assert self.vfs.read_file("file1.py") == "version 1"
    
    def test_diff_generation(self):
        """Test diff between commits."""
        self.vfs.write_file("file1.py", "original")
        commit1 = self.vfs.commit("Initial")
        
        self.vfs.write_file("file1.py", "modified")
        self.vfs.write_file("file2.py", "new")
        
        diff = self.vfs.get_diff(commit1)
        
        assert "file1.py" in diff
        assert diff["file1.py"]["status"] == "modified"
        assert "file2.py" in diff
        assert diff["file2.py"]["status"] == "added"
    
    def test_branching(self):
        """Test branch creation and switching."""
        # Create initial commit
        self.vfs.write_file("file.py", "main version")
        commit1 = self.vfs.commit("Initial")
        
        # Create branch
        success = self.vfs.create_branch("feature", commit1)
        assert success
        assert "feature" in self.vfs.branches
        
        # Switch to branch
        success = self.vfs.switch_branch("feature")
        assert success
        assert self.vfs.current_branch == "feature"
    
    def test_export_to_disk(self):
        """Test exporting VFS to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            self.vfs.write_file("test.py", "print('test')")
            self.vfs.write_file("subdir/file.py", "# subdir")
            
            self.vfs.export_to_disk(tmppath)
            
            assert (tmppath / "test.py").exists()
            assert (tmppath / "subdir" / "file.py").exists()
            assert (tmppath / "test.py").read_text() == "print('test')"
    
    def test_import_from_disk(self):
        """Test importing files from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create test files
            (tmppath / "file1.py").write_text("# file 1")
            (tmppath / "subdir").mkdir()
            (tmppath / "subdir" / "file2.py").write_text("# file 2")
            
            self.vfs.import_from_disk(tmppath)
            
            assert self.vfs.read_file("file1.py") == "# file 1"
            assert self.vfs.read_file("subdir/file2.py") == "# file 2"
    
    def test_save_and_load_json(self):
        """Test JSON serialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "vfs.json"
            
            # Create VFS with some data
            self.vfs.write_file("test.py", "print('test')")
            commit1 = self.vfs.commit("Initial")
            
            # Save to JSON
            self.vfs.save_to_json(json_path)
            assert json_path.exists()
            
            # Load from JSON
            loaded_vfs = VirtualFileSystem.load_from_json(json_path)
            
            assert loaded_vfs.project_id == self.vfs.project_id
            assert loaded_vfs.read_file("test.py") == "print('test')"
            assert len(loaded_vfs.commits) == 1
    
    def test_get_status(self):
        """Test VFS status reporting."""
        self.vfs.write_file("file1.py", "content")
        self.vfs.write_file("file2.py", "content")
        
        status = self.vfs.get_status()
        
        assert status["project_id"] == 999
        assert status["total_files"] == 2
        assert status["changed_files"] == 2
    
    def test_get_history(self):
        """Test commit history."""
        self.vfs.write_file("file.py", "v1")
        self.vfs.commit("First commit")
        
        self.vfs.write_file("file.py", "v2")
        self.vfs.commit("Second commit")
        
        history = self.vfs.get_history()
        
        assert len(history) == 2
        assert history[0]["message"] == "Second commit"
        assert history[1]["message"] == "First commit"


class TestASTPatcher:
    """Test AST-aware patching."""
    
    def test_analyze_simple_changes(self):
        """Test change analysis."""
        old_code = """
def foo():
    return 1
"""
        new_code = """
def foo():
    return 2

def bar():
    return 3
"""
        
        can_patch, reason, changes = PythonASTPatcher.analyze_changes(old_code, new_code)
        
        # Should detect changes (at least foo modified, possibly bar added)
        assert can_patch
        assert len(changes) >= 1
    
    def test_generate_patch_function_add(self):
        """Test patch generation for new function."""
        old_code = """
def existing():
    pass
"""
        new_code = """
def existing():
    pass

def new_function():
    return 42
"""
        
        patch = PythonASTPatcher.generate_patch(old_code, new_code, "test.py")
        
        assert patch is not None
        assert patch.patch_type in ["function_add", "full_replace"]
    
    def test_generate_patch_function_modify(self):
        """Test patch generation for modified function."""
        old_code = """
def calculate(x):
    return x * 2
"""
        new_code = """
def calculate(x):
    return x * 3
"""
        
        patch = PythonASTPatcher.generate_patch(old_code, new_code, "test.py")
        
        assert patch is not None
        assert patch.file_path == "test.py"
    
    def test_apply_patch_function_add(self):
        """Test applying a function addition patch."""
        old_code = "def old(): pass"
        
        patch = CodePatch(
            file_path="test.py",
            patch_type="function_add",
            target="new_func",
            content="def new_func():\n    return 42"
        )
        
        result = PythonASTPatcher.apply_patch(old_code, patch)
        
        assert "def old(): pass" in result
        assert "def new_func():" in result
    
    def test_apply_patch_full_replace(self):
        """Test full replacement patch."""
        old_code = "old content"
        
        patch = CodePatch(
            file_path="test.py",
            patch_type="full_replace",
            content="new content"
        )
        
        result = PythonASTPatcher.apply_patch(old_code, patch)
        
        assert result == "new content"
    
    def test_generate_patch_syntax_error(self):
        """Test patch generation with syntax errors."""
        old_code = "def foo(): pass"
        new_code = "def bar( invalid syntax"
        
        patch = PythonASTPatcher.generate_patch(old_code, new_code, "test.py")
        
        # Should fall back to full replacement
        assert patch.patch_type == "full_replace"
    
    def test_generate_patch_javascript(self):
        """Test JavaScript patching (full replacement)."""
        old_code = "function old() {}"
        new_code = "function new() {}"
        
        patch = generate_patch(old_code, new_code, "test.js")
        
        assert patch.patch_type == "full_replace"
        assert patch.content == new_code
    
    def test_apply_patch_python(self):
        """Test applying patch to Python file."""
        old_code = "def foo(): pass"
        new_code = "def foo(): return 1"
        
        patch = generate_patch(old_code, new_code, "test.py")
        result = apply_patch(old_code, patch)
        
        assert isinstance(result, str)
        assert len(result) > 0


class TestVFSGlobalManager:
    """Test VFS global manager."""
    
    def test_get_vfs_creates_new(self):
        """Test that get_vfs creates new VFS."""
        clear_vfs(777)  # Clean up first
        
        vfs = get_vfs(777)
        assert vfs.project_id == 777
        
        clear_vfs(777)
    
    def test_get_vfs_returns_same_instance(self):
        """Test that get_vfs returns same instance."""
        clear_vfs(888)
        
        vfs1 = get_vfs(888)
        vfs2 = get_vfs(888)
        
        assert vfs1 is vfs2
        
        clear_vfs(888)


# Run tests with:
# cd backend
# pytest tests/test_phase2.py -v
