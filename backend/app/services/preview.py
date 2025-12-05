"""Preview sandbox service for ephemeral Docker environments."""
import asyncio
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

import docker
from docker.errors import DockerException, NotFound

from ..core.config import settings
from ..core.logging import logger
from .vfs import get_vfs

# Docker client (lazily initialized)
_docker_client: Optional[docker.DockerClient] = None

# Preview container registry
_preview_registry: Dict[int, "PreviewEnvironment"] = {}

# Cleanup task
_cleanup_task: Optional[asyncio.Task] = None


def get_docker_client() -> docker.DockerClient:
    """Get or create Docker client."""
    global _docker_client
    if _docker_client is None:
        try:
            _docker_client = docker.from_env()
            logger.info("✅ Docker client initialized")
        except DockerException as e:
            logger.error(f"❌ Failed to connect to Docker: {e}")
            raise RuntimeError("Docker is not available") from e
    return _docker_client


@dataclass
class PreviewEnvironment:
    """Represents a preview environment."""
    
    project_id: int
    preview_id: str
    container_id: Optional[str] = None
    container_name: str = ""
    status: str = "creating"  # creating, running, stopped, error
    port: Optional[int] = None
    url: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    
    @property
    def is_expired(self) -> bool:
        """Check if preview has expired (1 hour)."""
        return datetime.now(timezone.utc) - self.created_at > timedelta(hours=1)
    
    @property
    def is_idle(self) -> bool:
        """Check if preview has been idle (30 minutes)."""
        return datetime.now(timezone.utc) - self.last_accessed > timedelta(minutes=30)
    
    def touch(self):
        """Update last accessed time."""
        self.last_accessed = datetime.now(timezone.utc)
    
    def add_log(self, message: str):
        """Add log message."""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        logger.info(f"[Preview {self.preview_id}] {message}")


class PreviewService:
    """Service for managing Docker-based preview environments."""
    
    def __init__(self):
        self.client = get_docker_client()
        self.network_name = "istudiox-preview-network"
        self._ensure_network()
    
    def _ensure_network(self):
        """Ensure preview network exists."""
        try:
            self.client.networks.get(self.network_name)
            logger.info(f"✅ Using existing network: {self.network_name}")
        except NotFound:
            self.client.networks.create(
                self.network_name,
                driver="bridge",
                labels={"istudiox": "preview"}
            )
            logger.info(f"✅ Created network: {self.network_name}")
    
    async def create_preview(
        self,
        project_id: int,
        files: Optional[Dict[str, str]] = None
    ) -> PreviewEnvironment:
        """Create a new preview environment.
        
        Args:
            project_id: Project ID
            files: Optional files dict, otherwise load from VFS
            
        Returns:
            PreviewEnvironment instance
        """
        preview_id = secrets.token_urlsafe(8)
        container_name = f"istudiox-preview-{preview_id}"
        
        preview = PreviewEnvironment(
            project_id=project_id,
            preview_id=preview_id,
            container_name=container_name
        )
        
        _preview_registry[project_id] = preview
        preview.add_log("Creating preview environment...")
        
        try:
            # Get files from VFS if not provided
            if files is None:
                vfs = get_vfs(project_id)
                files = vfs.list_files()
                if not files:
                    raise ValueError("No files in VFS")
                preview.add_log(f"Loaded {len(files)} files from VFS")
            
            # Detect project type
            project_type = self._detect_project_type(files)
            preview.add_log(f"Detected project type: {project_type}")
            
            # Create temporary directory for project files
            temp_dir = Path(settings.WORK_DIR) / "previews" / preview_id
            temp_dir.mkdir(parents=True, exist_ok=True)
            preview.add_log(f"Created temp directory: {temp_dir}")
            
            # Write files to temp directory
            for filepath, content in files.items():
                full_path = temp_dir / filepath
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
            preview.add_log(f"Wrote {len(files)} files to temp directory")
            
            # Build and start container based on project type
            if project_type == "python":
                await self._create_python_preview(preview, temp_dir)
            elif project_type == "nodejs":
                await self._create_nodejs_preview(preview, temp_dir)
            elif project_type == "react":
                await self._create_react_preview(preview, temp_dir)
            else:
                await self._create_static_preview(preview, temp_dir)
            
            preview.status = "running"
            preview.add_log(f"✅ Preview running at {preview.url}")
            
        except Exception as e:
            preview.status = "error"
            preview.error_message = str(e)
            preview.add_log(f"❌ Error: {e}")
            logger.error(f"Failed to create preview {preview_id}: {e}", exc_info=True)
        
        return preview
    
    def _detect_project_type(self, files: Dict[str, str]) -> str:
        """Detect project type from files."""
        if "requirements.txt" in files or "pyproject.toml" in files:
            return "python"
        if "package.json" in files:
            pkg_json = json.loads(files.get("package.json", "{}"))
            if "react" in pkg_json.get("dependencies", {}):
                return "react"
            return "nodejs"
        if "index.html" in files:
            return "static"
        return "unknown"
    
    async def _create_python_preview(
        self,
        preview: PreviewEnvironment,
        temp_dir: Path
    ):
        """Create Python/FastAPI preview."""
        preview.add_log("Building Python container...")
        
        # Create Dockerfile if not exists
        dockerfile_path = temp_dir / "Dockerfile"
        if not dockerfile_path.exists():
            dockerfile_content = """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
"""
            dockerfile_path.write_text(dockerfile_content)
            preview.add_log("Created Dockerfile")
        
        # Build image
        image_tag = f"istudiox-preview-{preview.preview_id}"
        try:
            image, logs = self.client.images.build(
                path=str(temp_dir),
                tag=image_tag,
                rm=True,
                forcerm=True
            )
            for log in logs:
                if "stream" in log:
                    preview.add_log(log["stream"].strip())
        except Exception as e:
            raise RuntimeError(f"Failed to build image: {e}")
        
        # Find available port
        port = self._find_available_port()
        preview.port = port
        
        # Start container
        container = self.client.containers.run(
            image_tag,
            name=preview.container_name,
            detach=True,
            ports={"8000/tcp": port},
            network=self.network_name,
            labels={
                "istudiox": "preview",
                "project_id": str(preview.project_id),
                "preview_id": preview.preview_id
            },
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=50000,  # 50% of 1 CPU
            remove=False
        )
        
        preview.container_id = container.id
        preview.url = f"http://localhost:{port}"
        preview.add_log(f"Container started: {container.short_id}")
        
        # Wait for container to be healthy
        await self._wait_for_container(preview)
    
    async def _create_nodejs_preview(
        self,
        preview: PreviewEnvironment,
        temp_dir: Path
    ):
        """Create Node.js preview."""
        preview.add_log("Building Node.js container...")
        
        # Create Dockerfile if not exists
        dockerfile_path = temp_dir / "Dockerfile"
        if not dockerfile_path.exists():
            dockerfile_content = """FROM node:18-slim
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
"""
            dockerfile_path.write_text(dockerfile_content)
            preview.add_log("Created Dockerfile")
        
        # Build image
        image_tag = f"istudiox-preview-{preview.preview_id}"
        image, logs = self.client.images.build(
            path=str(temp_dir),
            tag=image_tag,
            rm=True,
            forcerm=True
        )
        
        # Find available port
        port = self._find_available_port()
        preview.port = port
        
        # Start container
        container = self.client.containers.run(
            image_tag,
            name=preview.container_name,
            detach=True,
            ports={"3000/tcp": port},
            network=self.network_name,
            labels={
                "istudiox": "preview",
                "project_id": str(preview.project_id),
                "preview_id": preview.preview_id
            },
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=50000,
            remove=False
        )
        
        preview.container_id = container.id
        preview.url = f"http://localhost:{port}"
        preview.add_log(f"Container started: {container.short_id}")
        
        await self._wait_for_container(preview)
    
    async def _create_react_preview(
        self,
        preview: PreviewEnvironment,
        temp_dir: Path
    ):
        """Create React preview with Vite."""
        preview.add_log("Building React container...")
        
        # Create Dockerfile for Vite
        dockerfile_path = temp_dir / "Dockerfile"
        if not dockerfile_path.exists():
            dockerfile_content = """FROM node:18-slim
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
"""
            dockerfile_path.write_text(dockerfile_content)
            preview.add_log("Created Dockerfile for Vite")
        
        # Build and start container
        image_tag = f"istudiox-preview-{preview.preview_id}"
        image, logs = self.client.images.build(
            path=str(temp_dir),
            tag=image_tag,
            rm=True,
            forcerm=True
        )
        
        port = self._find_available_port()
        preview.port = port
        
        container = self.client.containers.run(
            image_tag,
            name=preview.container_name,
            detach=True,
            ports={"5173/tcp": port},
            network=self.network_name,
            labels={
                "istudiox": "preview",
                "project_id": str(preview.project_id),
                "preview_id": preview.preview_id
            },
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=50000,
            remove=False
        )
        
        preview.container_id = container.id
        preview.url = f"http://localhost:{port}"
        preview.add_log(f"Container started: {container.short_id}")
        
        await self._wait_for_container(preview)
    
    async def _create_static_preview(
        self,
        preview: PreviewEnvironment,
        temp_dir: Path
    ):
        """Create static HTML preview with nginx."""
        preview.add_log("Building static site container...")
        
        # Create nginx config
        nginx_conf = """server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
}
"""
        (temp_dir / "nginx.conf").write_text(nginx_conf)
        
        # Create Dockerfile
        dockerfile_content = """FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY . /usr/share/nginx/html
EXPOSE 80
"""
        (temp_dir / "Dockerfile").write_text(dockerfile_content)
        preview.add_log("Created nginx Dockerfile")
        
        # Build and start
        image_tag = f"istudiox-preview-{preview.preview_id}"
        image, logs = self.client.images.build(
            path=str(temp_dir),
            tag=image_tag,
            rm=True,
            forcerm=True
        )
        
        port = self._find_available_port()
        preview.port = port
        
        container = self.client.containers.run(
            image_tag,
            name=preview.container_name,
            detach=True,
            ports={"80/tcp": port},
            network=self.network_name,
            labels={
                "istudiox": "preview",
                "project_id": str(preview.project_id),
                "preview_id": preview.preview_id
            },
            mem_limit="256m",
            cpu_period=100000,
            cpu_quota=25000,  # 25% of 1 CPU
            remove=False
        )
        
        preview.container_id = container.id
        preview.url = f"http://localhost:{port}"
        preview.add_log(f"Container started: {container.short_id}")
        
        await self._wait_for_container(preview)
    
    def _find_available_port(self, start: int = 8100, end: int = 8200) -> int:
        """Find an available port in the range."""
        import socket
        for port in range(start, end):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("", port))
                    return port
                except OSError:
                    continue
        raise RuntimeError("No available ports in range")
    
    async def _wait_for_container(
        self,
        preview: PreviewEnvironment,
        timeout: int = 60
    ):
        """Wait for container to be healthy."""
        preview.add_log("Waiting for container to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                container = self.client.containers.get(preview.container_id)
                status = container.status
                
                if status == "running":
                    preview.add_log("Container is running")
                    await asyncio.sleep(2)  # Wait for app to start
                    return
                elif status in ("exited", "dead"):
                    logs = container.logs(tail=50).decode("utf-8")
                    raise RuntimeError(f"Container failed: {logs}")
                
            except Exception as e:
                raise RuntimeError(f"Failed to check container: {e}")
            
            await asyncio.sleep(1)
        
        raise TimeoutError("Container failed to start within timeout")
    
    async def update_preview(
        self,
        project_id: int,
        files: Dict[str, str]
    ) -> PreviewEnvironment:
        """Update preview with new files (hot reload).
        
        Args:
            project_id: Project ID
            files: New files to update
            
        Returns:
            Updated PreviewEnvironment
        """
        preview = _preview_registry.get(project_id)
        if not preview:
            # Create new preview if doesn't exist
            return await self.create_preview(project_id, files)
        
        preview.touch()
        preview.add_log("Updating preview with new files...")
        
        try:
            # For now, recreate container (future: hot reload)
            await self.stop_preview(project_id)
            return await self.create_preview(project_id, files)
            
        except Exception as e:
            preview.add_log(f"❌ Update failed: {e}")
            logger.error(f"Failed to update preview {preview.preview_id}: {e}")
            raise
    
    async def stop_preview(self, project_id: int) -> bool:
        """Stop and remove preview container.
        
        Args:
            project_id: Project ID
            
        Returns:
            True if stopped, False if not found
        """
        preview = _preview_registry.get(project_id)
        if not preview:
            return False
        
        preview.add_log("Stopping preview...")
        
        try:
            if preview.container_id:
                container = self.client.containers.get(preview.container_id)
                container.stop(timeout=10)
                container.remove()
                preview.add_log("Container stopped and removed")
            
            # Cleanup temp directory
            temp_dir = Path(settings.WORK_DIR) / "previews" / preview.preview_id
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
                preview.add_log("Temp directory cleaned up")
            
            # Remove image
            try:
                image_tag = f"istudiox-preview-{preview.preview_id}"
                self.client.images.remove(image_tag, force=True)
                preview.add_log("Image removed")
            except Exception:
                pass
            
            preview.status = "stopped"
            del _preview_registry[project_id]
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop preview {preview.preview_id}: {e}")
            return False
    
    def get_preview(self, project_id: int) -> Optional[PreviewEnvironment]:
        """Get preview environment.
        
        Args:
            project_id: Project ID
            
        Returns:
            PreviewEnvironment or None
        """
        preview = _preview_registry.get(project_id)
        if preview:
            preview.touch()
        return preview
    
    def get_preview_logs(self, project_id: int) -> List[str]:
        """Get preview logs.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of log messages
        """
        preview = _preview_registry.get(project_id)
        if not preview:
            return []
        
        logs = preview.logs.copy()
        
        # Also get container logs if available
        if preview.container_id:
            try:
                container = self.client.containers.get(preview.container_id)
                container_logs = container.logs(tail=50).decode("utf-8")
                logs.append("\n--- Container Logs ---")
                logs.extend(container_logs.split("\n"))
            except Exception:
                pass
        
        return logs
    
    async def cleanup_expired_previews(self):
        """Cleanup expired or idle previews."""
        to_remove = []
        
        for project_id, preview in _preview_registry.items():
            if preview.is_expired or preview.is_idle:
                logger.info(f"Cleaning up expired preview {preview.preview_id}")
                to_remove.append(project_id)
        
        for project_id in to_remove:
            await self.stop_preview(project_id)
    
    def list_previews(self) -> List[PreviewEnvironment]:
        """List all active previews."""
        return list(_preview_registry.values())


# Singleton instance
_preview_service: Optional[PreviewService] = None


def get_preview_service() -> PreviewService:
    """Get or create preview service singleton."""
    global _preview_service
    if _preview_service is None:
        _preview_service = PreviewService()
    return _preview_service


async def start_cleanup_task():
    """Start background cleanup task."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_loop())
        logger.info("✅ Preview cleanup task started")


async def _cleanup_loop():
    """Background loop to cleanup expired previews."""
    service = get_preview_service()
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            await service.cleanup_expired_previews()
        except Exception as e:
            logger.error(f"Cleanup task error: {e}", exc_info=True)


async def stop_cleanup_task():
    """Stop background cleanup task."""
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
        logger.info("✅ Preview cleanup task stopped")
