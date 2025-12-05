"""Preview API endpoints."""
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.preview import get_preview_service, start_cleanup_task
from ..services.vfs_watcher import start_vfs_watcher, stop_vfs_watcher

router = APIRouter(prefix="/preview", tags=["preview"])


class CreatePreviewRequest(BaseModel):
    """Request to create preview."""
    project_id: int
    files: Optional[Dict[str, str]] = None


class PreviewResponse(BaseModel):
    """Preview environment response."""
    project_id: int
    preview_id: str
    status: str
    url: Optional[str] = None
    port: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str
    last_accessed: str


class PreviewLogsResponse(BaseModel):
    """Preview logs response."""
    logs: List[str]


@router.on_event("startup")
async def startup():
    """Start cleanup task on router startup."""
    await start_cleanup_task()


@router.post("/", response_model=PreviewResponse)
async def create_preview(request: CreatePreviewRequest):
    """Create a new preview environment with live reload.
    
    POST /preview/
    {
        "project_id": 1,
        "files": {
            "main.py": "...",
            "requirements.txt": "..."
        }
    }
    
    Returns:
        Preview environment details with URL
    """
    service = get_preview_service()
    
    try:
        # Create preview environment
        preview = await service.create_preview(
            project_id=request.project_id,
            files=request.files
        )
        
        # Start VFS watcher for live reload
        start_vfs_watcher(request.project_id, poll_interval=2.0)
        
        return PreviewResponse(
            project_id=preview.project_id,
            preview_id=preview.preview_id,
            status=preview.status,
            url=preview.url,
            port=preview.port,
            error_message=preview.error_message,
            created_at=preview.created_at.isoformat(),
            last_accessed=preview.last_accessed.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}", response_model=PreviewResponse)
async def get_preview(project_id: int):
    """Get preview environment status.
    
    GET /preview/1
    
    Returns:
        Preview environment details
    """
    service = get_preview_service()
    preview = service.get_preview(project_id)
    
    if not preview:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    return PreviewResponse(
        project_id=preview.project_id,
        preview_id=preview.preview_id,
        status=preview.status,
        url=preview.url,
        port=preview.port,
        error_message=preview.error_message,
        created_at=preview.created_at.isoformat(),
        last_accessed=preview.last_accessed.isoformat()
    )


@router.put("/{project_id}", response_model=PreviewResponse)
async def update_preview(project_id: int, files: Dict[str, str]):
    """Update preview with new files (hot reload).
    
    PUT /preview/1
    {
        "main.py": "# Updated code",
        "requirements.txt": "fastapi==0.109.0"
    }
    
    Returns:
        Updated preview environment
    """
    service = get_preview_service()
    
    try:
        preview = await service.update_preview(project_id, files)
        
        return PreviewResponse(
            project_id=preview.project_id,
            preview_id=preview.preview_id,
            status=preview.status,
            url=preview.url,
            port=preview.port,
            error_message=preview.error_message,
            created_at=preview.created_at.isoformat(),
            last_accessed=preview.last_accessed.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def stop_preview(project_id: int):
    """Stop and remove preview environment.
    
    DELETE /preview/1
    
    Returns:
        Success message
    """
    service = get_preview_service()
    
    # Stop VFS watcher
    stop_vfs_watcher(project_id)
    
    # Stop preview
    success = await service.stop_preview(project_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    return {"message": "Preview stopped successfully"}


@router.get("/{project_id}/logs", response_model=PreviewLogsResponse)
async def get_preview_logs(project_id: int):
    """Get preview container logs.
    
    GET /preview/1/logs
    
    Returns:
        Preview logs
    """
    service = get_preview_service()
    logs = service.get_preview_logs(project_id)
    
    if not logs:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    return PreviewLogsResponse(logs=logs)


@router.get("/")
async def list_previews():
    """List all active preview environments.
    
    GET /preview/
    
    Returns:
        List of preview environments
    """
    service = get_preview_service()
    previews = service.list_previews()
    
    return {
        "previews": [
            PreviewResponse(
                project_id=p.project_id,
                preview_id=p.preview_id,
                status=p.status,
                url=p.url,
                port=p.port,
                error_message=p.error_message,
                created_at=p.created_at.isoformat(),
                last_accessed=p.last_accessed.isoformat()
            )
            for p in previews
        ]
    }
