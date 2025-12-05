"""VFS watcher for live preview updates."""
import asyncio
from typing import Callable, Dict, Optional, Set

from ..core.logging import logger
from ..core.sockets import manager
from .preview import get_preview_service
from .vfs import VFS, get_vfs

# Global watcher registry: project_id -> watcher task
_watchers: Dict[int, asyncio.Task] = {}

# VFS commit callbacks
_commit_callbacks: Dict[int, Set[Callable]] = {}


class VFSWatcher:
    """Watches VFS for commits and triggers preview updates."""
    
    def __init__(self, project_id: int, poll_interval: float = 1.0):
        self.project_id = project_id
        self.poll_interval = poll_interval
        self.vfs: Optional[VFS] = None
        self.last_commit_id: Optional[str] = None
        self.running = False
    
    async def start(self):
        """Start watching VFS for changes."""
        self.vfs = get_vfs(self.project_id)
        self.last_commit_id = self.vfs.current_commit_id
        self.running = True
        
        logger.info(f"🔍 Started VFS watcher for project {self.project_id}")
        
        while self.running:
            try:
                await asyncio.sleep(self.poll_interval)
                await self._check_for_changes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"VFS watcher error for project {self.project_id}: {e}")
        
        logger.info(f"🔍 Stopped VFS watcher for project {self.project_id}")
    
    async def _check_for_changes(self):
        """Check if VFS has new commits."""
        current_commit = self.vfs.current_commit_id
        
        if current_commit and current_commit != self.last_commit_id:
            logger.info(
                f"📝 VFS change detected for project {self.project_id}: "
                f"{self.last_commit_id[:8] if self.last_commit_id else 'None'} -> {current_commit[:8]}"
            )
            
            # Trigger preview update
            await self._trigger_preview_update()
            
            # Broadcast change to connected clients
            await manager.broadcast("reload", str(self.project_id))

            # Call registered callbacks
            await self._call_callbacks()
            
            self.last_commit_id = current_commit
    
    async def _trigger_preview_update(self):
        """Trigger preview environment update."""
        try:
            preview_service = get_preview_service()
            preview = preview_service.get_preview(self.project_id)
            
            if preview:
                # Get latest files from VFS
                files = self.vfs.list_files()
                
                # Update preview (hot reload)
                await preview_service.update_preview(self.project_id, files)
                logger.info(f"✅ Preview updated for project {self.project_id}")
            else:
                logger.debug(f"No active preview for project {self.project_id}")
        
        except Exception as e:
            logger.error(f"Failed to update preview for project {self.project_id}: {e}")
    
    async def _call_callbacks(self):
        """Call registered callbacks."""
        callbacks = _commit_callbacks.get(self.project_id, set())
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.project_id, self.vfs.current_commit_id)
                else:
                    callback(self.project_id, self.vfs.current_commit_id)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def stop(self):
        """Stop watching."""
        self.running = False


def start_vfs_watcher(project_id: int, poll_interval: float = 1.0) -> asyncio.Task:
    """Start VFS watcher for a project.
    
    Args:
        project_id: Project ID to watch
        poll_interval: Polling interval in seconds
        
    Returns:
        asyncio.Task running the watcher
    """
    # Stop existing watcher if any
    stop_vfs_watcher(project_id)
    
    # Create and start new watcher
    watcher = VFSWatcher(project_id, poll_interval)
    task = asyncio.create_task(watcher.start())
    _watchers[project_id] = task
    
    logger.info(f"✅ VFS watcher started for project {project_id}")
    return task


def stop_vfs_watcher(project_id: int):
    """Stop VFS watcher for a project.
    
    Args:
        project_id: Project ID
    """
    task = _watchers.get(project_id)
    if task and not task.done():
        task.cancel()
        del _watchers[project_id]
        logger.info(f"✅ VFS watcher stopped for project {project_id}")


def register_commit_callback(project_id: int, callback: Callable):
    """Register a callback for VFS commits.
    
    Args:
        project_id: Project ID
        callback: Callback function(project_id, commit_id)
    """
    if project_id not in _commit_callbacks:
        _commit_callbacks[project_id] = set()
    _commit_callbacks[project_id].add(callback)


def unregister_commit_callback(project_id: int, callback: Callable):
    """Unregister a commit callback.
    
    Args:
        project_id: Project ID
        callback: Callback function to remove
    """
    if project_id in _commit_callbacks:
        _commit_callbacks[project_id].discard(callback)


def stop_all_watchers():
    """Stop all VFS watchers."""
    for project_id in list(_watchers.keys()):
        stop_vfs_watcher(project_id)
    logger.info("✅ All VFS watchers stopped")
