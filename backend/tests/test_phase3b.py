"""Tests for Phase 3B: Preview Sandbox."""
import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.services.preview import (
    PreviewService,
    PreviewEnvironment,
    get_preview_service,
)
from app.services.vfs import get_vfs, clear_vfs
from app.services.vfs_watcher import (
    start_vfs_watcher,
    stop_vfs_watcher,
    register_commit_callback,
)


# Mock Docker to avoid requiring Docker in tests
@pytest.fixture
def mock_docker():
    """Mock Docker client."""
    with patch("app.services.preview.docker") as mock_docker:
        # Mock client
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        
        # Mock network
        mock_network = MagicMock()
        mock_client.networks.get.return_value = mock_network
        
        # Mock container
        mock_container = MagicMock()
        mock_container.id = "mock-container-id"
        mock_container.short_id = "mock123"
        mock_container.status = "running"
        mock_container.logs.return_value = b"Container logs"
        mock_client.containers.run.return_value = mock_container
        mock_client.containers.get.return_value = mock_container
        
        # Mock image build
        mock_image = MagicMock()
        mock_client.images.build.return_value = (mock_image, [{"stream": "Step 1/5"}])
        
        yield mock_client


class TestPreviewEnvironment:
    """Test PreviewEnvironment dataclass."""
    
    def test_preview_environment_creation(self):
        """Test creating preview environment."""
        preview = PreviewEnvironment(
            project_id=1,
            preview_id="test123",
            container_name="istudiox-preview-test123"
        )
        
        assert preview.project_id == 1
        assert preview.preview_id == "test123"
        assert preview.status == "creating"
        assert preview.url is None
        assert not preview.is_expired
        assert not preview.is_idle
    
    def test_preview_touch(self):
        """Test updating last accessed time."""
        preview = PreviewEnvironment(
            project_id=1,
            preview_id="test123",
            container_name="istudiox-preview-test123"
        )
        
        old_time = preview.last_accessed
        preview.touch()
        assert preview.last_accessed >= old_time
    
    def test_preview_add_log(self):
        """Test adding log messages."""
        preview = PreviewEnvironment(
            project_id=1,
            preview_id="test123",
            container_name="istudiox-preview-test123"
        )
        
        preview.add_log("Test message")
        assert len(preview.logs) == 1
        assert "Test message" in preview.logs[0]


class TestPreviewService:
    """Test PreviewService."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test."""
        # Clear VFS
        clear_vfs(1)
        yield
        clear_vfs(1)
    
    def test_detect_project_type_python(self, mock_docker):
        """Test detecting Python project."""
        service = PreviewService()
        
        files = {
            "main.py": "print('hello')",
            "requirements.txt": "fastapi==0.110.0"
        }
        
        project_type = service._detect_project_type(files)
        assert project_type == "python"
    
    def test_detect_project_type_react(self, mock_docker):
        """Test detecting React project."""
        service = PreviewService()
        
        files = {
            "package.json": '{"dependencies": {"react": "^18.0.0"}}',
            "src/App.jsx": "export default function App() {}"
        }
        
        project_type = service._detect_project_type(files)
        assert project_type == "react"
    
    def test_detect_project_type_nodejs(self, mock_docker):
        """Test detecting Node.js project."""
        service = PreviewService()
        
        files = {
            "package.json": '{"dependencies": {"express": "^4.0.0"}}',
            "index.js": "const express = require('express')"
        }
        
        project_type = service._detect_project_type(files)
        assert project_type == "nodejs"
    
    def test_detect_project_type_static(self, mock_docker):
        """Test detecting static HTML project."""
        service = PreviewService()
        
        files = {
            "index.html": "<html><body>Hello</body></html>",
            "style.css": "body { margin: 0; }"
        }
        
        project_type = service._detect_project_type(files)
        assert project_type == "static"
    
    async def test_create_preview_python(self, mock_docker):
        """Test creating Python preview."""
        service = PreviewService()
        
        files = {
            "main.py": """
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello"}
""",
            "requirements.txt": "fastapi==0.110.0\nuvicorn==0.30.0"
        }
        
        # Store files in VFS
        vfs = get_vfs(1)
        for filepath, content in files.items():
            vfs.write_file(filepath, content)
        vfs.commit("Initial commit")
        
        # Create preview
        preview = await service.create_preview(1, files)
        
        assert preview.project_id == 1
        assert preview.preview_id
        assert preview.container_name.startswith("istudiox-preview-")
        assert preview.status in ("creating", "running")
        assert len(preview.logs) > 0
    
    async def test_create_preview_from_vfs(self, mock_docker):
        """Test creating preview from VFS."""
        service = PreviewService()
        
        # Store files in VFS
        vfs = get_vfs(1)
        vfs.write_file("index.html", "<html><body>Test</body></html>")
        vfs.commit("Initial commit")
        
        # Create preview without explicit files
        preview = await service.create_preview(1)
        
        assert preview.project_id == 1
        assert preview.preview_id
        assert "Loaded 1 files from VFS" in " ".join(preview.logs)
    
    async def test_get_preview(self, mock_docker):
        """Test getting preview."""
        service = PreviewService()
        
        # Create preview
        files = {"index.html": "<html><body>Test</body></html>"}
        preview = await service.create_preview(1, files)
        
        # Get preview
        retrieved = service.get_preview(1)
        
        assert retrieved is not None
        assert retrieved.project_id == 1
        assert retrieved.preview_id == preview.preview_id
    
    async def test_stop_preview(self, mock_docker):
        """Test stopping preview."""
        service = PreviewService()
        
        # Create preview
        files = {"index.html": "<html><body>Test</body></html>"}
        preview = await service.create_preview(1, files)
        
        # Stop preview
        success = await service.stop_preview(1)
        
        assert success
        
        # Preview should be gone
        retrieved = service.get_preview(1)
        assert retrieved is None
    
    async def test_update_preview(self, mock_docker):
        """Test updating preview (hot reload)."""
        service = PreviewService()
        
        # Create initial preview
        files_v1 = {"index.html": "<html><body>Version 1</body></html>"}
        preview_v1 = await service.create_preview(1, files_v1)
        
        # Update preview
        files_v2 = {"index.html": "<html><body>Version 2</body></html>"}
        preview_v2 = await service.update_preview(1, files_v2)
        
        assert preview_v2.project_id == 1
        assert "Updating preview" in " ".join(preview_v2.logs) or "Creating preview" in " ".join(preview_v2.logs)
    
    def test_get_preview_logs(self, mock_docker):
        """Test getting preview logs."""
        service = PreviewService()
        
        # Create preview with some logs
        preview = PreviewEnvironment(
            project_id=1,
            preview_id="test123",
            container_name="istudiox-preview-test123",
            container_id="mock-container-id"
        )
        preview.add_log("Log message 1")
        preview.add_log("Log message 2")
        
        from app.services.preview import _preview_registry
        _preview_registry[1] = preview
        
        # Get logs
        logs = service.get_preview_logs(1)
        
        assert len(logs) >= 2
        assert any("Log message 1" in log for log in logs)


class TestVFSWatcher:
    """Test VFS watcher for live reload."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test."""
        clear_vfs(1)
        stop_vfs_watcher(1)
        yield
        stop_vfs_watcher(1)
        clear_vfs(1)
    
    async def test_start_vfs_watcher(self):
        """Test starting VFS watcher."""
        # Setup VFS
        vfs = get_vfs(1)
        vfs.write_file("test.py", "print('hello')")
        vfs.commit("Initial commit")
        
        # Start watcher
        task = start_vfs_watcher(1, poll_interval=0.5)
        
        assert task is not None
        assert not task.done()
        
        # Cleanup
        stop_vfs_watcher(1)
        await asyncio.sleep(0.1)
    
    async def test_vfs_watcher_detects_changes(self, mock_docker):
        """Test VFS watcher detects commits."""
        from app.services.preview import get_preview_service
        
        # Setup VFS
        vfs = get_vfs(1)
        vfs.write_file("test.py", "print('hello')")
        vfs.commit("Initial commit")
        
        # Create preview
        preview_service = get_preview_service()
        files = {"test.py": "print('hello')"}
        await preview_service.create_preview(1, files)
        
        # Start watcher
        start_vfs_watcher(1, poll_interval=0.5)
        
        # Make a change
        vfs.write_file("test.py", "print('world')")
        vfs.commit("Update test.py")
        
        # Wait for watcher to detect change
        await asyncio.sleep(1.5)
        
        # Cleanup
        stop_vfs_watcher(1)
    
    async def test_vfs_watcher_callback(self):
        """Test VFS watcher callbacks."""
        # Setup VFS
        vfs = get_vfs(1)
        vfs.write_file("test.py", "print('hello')")
        vfs.commit("Initial commit")
        
        # Register callback
        callback_called = []
        
        def callback(project_id, commit_id):
            callback_called.append((project_id, commit_id))
        
        register_commit_callback(1, callback)
        
        # Start watcher
        start_vfs_watcher(1, poll_interval=0.5)
        
        # Make a change
        vfs.write_file("test.py", "print('world')")
        commit_id = vfs.commit("Update test.py")
        
        # Wait for callback
        await asyncio.sleep(1.5)
        
        # Check callback was called
        assert len(callback_called) > 0
        assert callback_called[0][0] == 1
        
        # Cleanup
        stop_vfs_watcher(1)


class TestPreviewIntegration:
    """Integration tests for preview system."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test."""
        clear_vfs(1)
        stop_vfs_watcher(1)
        yield
        stop_vfs_watcher(1)
        clear_vfs(1)
    
    async def test_end_to_end_preview_workflow(self, mock_docker):
        """Test complete preview workflow."""
        from app.services.preview import get_preview_service
        
        service = get_preview_service()
        
        # 1. Create initial project
        vfs = get_vfs(1)
        vfs.write_file("main.py", "print('version 1')")
        vfs.write_file("requirements.txt", "")
        vfs.commit("Initial commit")
        
        # 2. Create preview
        files = vfs.list_files()
        preview = await service.create_preview(1, files)
        
        assert preview.status in ("creating", "running")
        assert preview.url
        
        # 3. Start watcher
        start_vfs_watcher(1, poll_interval=0.5)
        
        # 4. Make an edit
        vfs.write_file("main.py", "print('version 2')")
        vfs.commit("Update main.py")
        
        # 5. Wait for auto-reload
        await asyncio.sleep(1.5)
        
        # 6. Stop preview
        success = await service.stop_preview(1)
        assert success
        
        # 7. Stop watcher
        stop_vfs_watcher(1)
    
    async def test_multiple_previews(self, mock_docker):
        """Test managing multiple preview environments."""
        from app.services.preview import get_preview_service
        
        service = get_preview_service()
        
        # Create previews for multiple projects
        for project_id in [1, 2, 3]:
            vfs = get_vfs(project_id)
            vfs.write_file("index.html", f"<html><body>Project {project_id}</body></html>")
            vfs.commit("Initial commit")
            
            files = vfs.list_files()
            preview = await service.create_preview(project_id, files)
            assert preview.project_id == project_id
        
        # List all previews
        previews = service.list_previews()
        assert len(previews) == 3
        
        # Stop all
        for project_id in [1, 2, 3]:
            await service.stop_preview(project_id)
            clear_vfs(project_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
