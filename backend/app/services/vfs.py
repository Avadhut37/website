"""Virtual File System with Git-like version control."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..core.logging import logger


class FileStatus(str, Enum):
    """File status in VFS."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


@dataclass
class FileNode:
    """A file in the VFS."""
    path: str
    content: str
    status: FileStatus = FileStatus.UNCHANGED
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "content": self.content,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "FileNode":
        """Create from dictionary."""
        return cls(
            path=data["path"],
            content=data["content"],
            status=FileStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            modified_at=datetime.fromisoformat(data["modified_at"])
        )


@dataclass
class Commit:
    """A VFS commit."""
    id: str
    message: str
    timestamp: datetime
    files: Dict[str, FileNode]
    parent_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "parent_id": self.parent_id,
            "files": {path: node.to_dict() for path, node in self.files.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Commit":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            message=data["message"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            parent_id=data.get("parent_id"),
            files={path: FileNode.from_dict(node) for path, node in data["files"].items()}
        )


class VirtualFileSystem:
    """
    In-memory file system with git-like commit history.
    
    Features:
    - Commit/rollback
    - Branching (basic)
    - Diff generation
    - Export to disk
    - Import from disk
    - JSON serialization for persistence
    """
    
    def __init__(self, project_id: int):
        self.project_id = project_id
        self.files: Dict[str, FileNode] = {}  # Current working tree
        self.commits: List[Commit] = []
        self.current_commit_id: Optional[str] = None
        self.branches: Dict[str, str] = {"main": None}  # branch -> commit_id
        self.current_branch = "main"
    
    def write_file(self, path: str, content: str) -> None:
        """Write or update a file in the VFS."""
        if path in self.files:
            old_node = self.files[path]
            if old_node.content != content:
                self.files[path] = FileNode(
                    path=path,
                    content=content,
                    status=FileStatus.MODIFIED,
                    created_at=old_node.created_at,
                    modified_at=datetime.utcnow()
                )
        else:
            self.files[path] = FileNode(
                path=path,
                content=content,
                status=FileStatus.ADDED
            )
    
    def read_file(self, path: str) -> Optional[str]:
        """Read a file from the VFS."""
        node = self.files.get(path)
        return node.content if node else None
    
    def delete_file(self, path: str) -> None:
        """Mark a file as deleted."""
        if path in self.files:
            self.files[path].status = FileStatus.DELETED
    
    def get_changed_files(self) -> Dict[str, FileNode]:
        """Get all files with changes."""
        return {
            path: node
            for path, node in self.files.items()
            if node.status != FileStatus.UNCHANGED
        }
    
    def commit(self, message: str) -> str:
        """Create a commit snapshot."""
        commit_id = hashlib.sha1(
            f"{self.project_id}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:8]
        
        # Deep copy current files
        snapshot = {}
        for path, node in self.files.items():
            if node.status != FileStatus.DELETED:
                snapshot[path] = FileNode(
                    path=node.path,
                    content=node.content,
                    status=FileStatus.UNCHANGED,  # Reset status
                    created_at=node.created_at,
                    modified_at=node.modified_at
                )
        
        commit = Commit(
            id=commit_id,
            message=message,
            timestamp=datetime.utcnow(),
            files=snapshot,
            parent_id=self.current_commit_id
        )
        
        self.commits.append(commit)
        self.current_commit_id = commit_id
        self.branches[self.current_branch] = commit_id
        
        # Mark all files as unchanged
        for node in self.files.values():
            if node.status != FileStatus.DELETED:
                node.status = FileStatus.UNCHANGED
        
        # Remove deleted files
        self.files = {path: node for path, node in self.files.items() 
                     if node.status != FileStatus.DELETED}
        
        logger.info(f"[VFS] Created commit {commit_id}: {message}")
        return commit_id
    
    def rollback(self, commit_id: str) -> bool:
        """Rollback to a specific commit."""
        commit = next((c for c in self.commits if c.id == commit_id), None)
        if not commit:
            logger.error(f"[VFS] Commit {commit_id} not found")
            return False
        
        # Restore files from commit
        self.files = {}
        for path, node in commit.files.items():
            self.files[path] = FileNode(
                path=node.path,
                content=node.content,
                status=FileStatus.UNCHANGED,
                created_at=node.created_at,
                modified_at=node.modified_at
            )
        
        self.current_commit_id = commit_id
        logger.info(f"[VFS] Rolled back to commit {commit_id}")
        return True
    
    def get_diff(self, from_commit: Optional[str] = None) -> Dict[str, Dict]:
        """Get diff between current state and a commit."""
        if not from_commit or not self.commits:
            # Diff against empty state
            return {
                path: {
                    "status": node.status.value,
                    "content": node.content
                }
                for path, node in self.files.items()
            }
        
        old_commit = next((c for c in self.commits if c.id == from_commit), None)
        if not old_commit:
            logger.error(f"[VFS] Commit {from_commit} not found")
            return {}
        
        old_files = old_commit.files
        diff = {}
        
        # Check for modifications and additions
        for path, node in self.files.items():
            if path not in old_files:
                diff[path] = {"status": "added", "content": node.content}
            elif old_files[path].content != node.content:
                diff[path] = {
                    "status": "modified",
                    "old_content": old_files[path].content,
                    "new_content": node.content
                }
        
        # Check for deletions
        for path in old_files:
            if path not in self.files:
                diff[path] = {"status": "deleted"}
        
        return diff
    
    def create_branch(self, branch_name: str, from_commit: Optional[str] = None) -> bool:
        """Create a new branch."""
        if branch_name in self.branches:
            logger.error(f"[VFS] Branch {branch_name} already exists")
            return False
        
        commit_id = from_commit or self.current_commit_id
        self.branches[branch_name] = commit_id
        logger.info(f"[VFS] Created branch {branch_name} from {commit_id}")
        return True
    
    def switch_branch(self, branch_name: str) -> bool:
        """Switch to a different branch."""
        if branch_name not in self.branches:
            logger.error(f"[VFS] Branch {branch_name} not found")
            return False
        
        commit_id = self.branches[branch_name]
        if commit_id:
            success = self.rollback(commit_id)
            if not success:
                return False
        
        self.current_branch = branch_name
        logger.info(f"[VFS] Switched to branch {branch_name}")
        return True
    
    def export_to_disk(self, base_path: Path) -> None:
        """Export VFS to disk."""
        base_path.mkdir(parents=True, exist_ok=True)
        
        for path, node in self.files.items():
            if node.status == FileStatus.DELETED:
                continue
            
            file_path = base_path / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(node.content, encoding="utf-8")
        
        logger.info(f"[VFS] Exported {len(self.files)} files to {base_path}")
    
    def import_from_disk(self, base_path: Path) -> None:
        """Import files from disk into VFS."""
        for file_path in base_path.rglob("*"):
            if file_path.is_file():
                relative_path = str(file_path.relative_to(base_path))
                content = file_path.read_text(encoding="utf-8")
                self.write_file(relative_path, content)
        
        logger.info(f"[VFS] Imported {len(self.files)} files from {base_path}")
    
    def save_to_json(self, file_path: Path) -> None:
        """Save VFS state to JSON file."""
        data = {
            "project_id": self.project_id,
            "current_branch": self.current_branch,
            "current_commit_id": self.current_commit_id,
            "branches": self.branches,
            "files": {path: node.to_dict() for path, node in self.files.items()},
            "commits": [commit.to_dict() for commit in self.commits]
        }
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"[VFS] Saved state to {file_path}")
    
    @classmethod
    def load_from_json(cls, file_path: Path) -> "VirtualFileSystem":
        """Load VFS state from JSON file."""
        data = json.loads(file_path.read_text(encoding="utf-8"))
        
        vfs = cls(data["project_id"])
        vfs.current_branch = data["current_branch"]
        vfs.current_commit_id = data.get("current_commit_id")
        vfs.branches = data["branches"]
        vfs.files = {path: FileNode.from_dict(node) for path, node in data["files"].items()}
        vfs.commits = [Commit.from_dict(commit) for commit in data["commits"]]
        
        logger.info(f"[VFS] Loaded state from {file_path}")
        return vfs
    
    def get_status(self) -> Dict:
        """Get VFS status."""
        changed = self.get_changed_files()
        return {
            "project_id": self.project_id,
            "current_branch": self.current_branch,
            "current_commit": self.current_commit_id,
            "total_files": len(self.files),
            "changed_files": len(changed),
            "changes": {path: node.status.value for path, node in changed.items()},
            "total_commits": len(self.commits),
            "branches": list(self.branches.keys())
        }
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get commit history."""
        return [
            {
                "id": commit.id,
                "message": commit.message,
                "timestamp": commit.timestamp.isoformat(),
                "files_count": len(commit.files),
                "parent_id": commit.parent_id
            }
            for commit in reversed(self.commits[-limit:])
        ]


# Global VFS manager
_vfs_instances: Dict[int, VirtualFileSystem] = {}

# Alias for backward compatibility
VFS = VirtualFileSystem

def get_vfs(project_id: int) -> VirtualFileSystem:
    """Get or create VFS for a project."""
    if project_id not in _vfs_instances:
        _vfs_instances[project_id] = VirtualFileSystem(project_id)
        logger.info(f"[VFS] Created new VFS for project {project_id}")
    return _vfs_instances[project_id]


def clear_vfs(project_id: int) -> None:
    """Clear VFS for a project."""
    if project_id in _vfs_instances:
        del _vfs_instances[project_id]
        logger.info(f"[VFS] Cleared VFS for project {project_id}")
