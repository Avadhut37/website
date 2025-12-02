"""AI generation endpoints."""
from typing import Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..ai.engine import get_ai_engine
from ..ai.providers.openrouter import OpenRouterProvider
from ..core.rate_limit import limiter, RATE_LIMITS
from ..core.config import settings

router = APIRouter()


class SpecPayload(BaseModel):
    spec: dict[str, Any]
    image: Optional[str] = None  # Base64 encoded image


class EditPayload(BaseModel):
    files: dict[str, str]
    instruction: str
    project_name: str = "ExistingProject"
    project_id: Optional[int] = None
    image: Optional[str] = None  # Base64 encoded image


class GenerationResponse(BaseModel):
    files: dict[str, str]
    file_count: int
    provider: str = "unknown"


@router.post("/preview", response_model=GenerationResponse)
@limiter.limit(RATE_LIMITS["generation"])
async def preview_generation(request: Request, payload: SpecPayload):
    """Preview code generation without saving to a project."""
    try:
        engine = get_ai_engine()
        # Use the async method directly
        project_name = payload.spec.get("name", payload.spec.get("raw", "GeneratedApp"))
        if isinstance(project_name, str) and len(project_name) > 50:
            project_name = project_name[:50]
            
        files = await engine.generate_project(
            payload.spec, 
            project_name,
            image_data=payload.image
        )
        provider = engine.providers[0].name if engine.providers else "fallback"
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    
    return GenerationResponse(
        files=files,
        file_count=len(files),
        provider=provider
    )


@router.post("/edit", response_model=GenerationResponse)
@limiter.limit(RATE_LIMITS["generation"])
async def edit_project(request: Request, payload: EditPayload):
    """Edit an existing project based on instructions."""
    try:
        engine = get_ai_engine()
        files = await engine.edit_project(
            payload.files,
            payload.instruction,
            payload.project_name,
            image_data=payload.image
        )
        
        # If project_id is provided, save the modified files to disk
        if payload.project_id:
            project_dir = Path(settings.WORK_DIR) / str(payload.project_id)
            if project_dir.exists():
                for rel_path, content in files.items():
                    # Security check
                    if ".." in rel_path or rel_path.startswith("/"):
                        continue
                        
                    file_path = project_dir / rel_path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding="utf-8")
        
        provider = engine.providers[0].name if engine.providers else "fallback"
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    
    return GenerationResponse(
        files=files,
        file_count=len(files),
        provider=provider
    )


@router.get("/models")
def list_models():
    """List available AI models."""
    return {
        "openrouter": OpenRouterProvider.list_models(),
        "current": get_ai_engine().get_status(),
    }


@router.get("/status")
def ai_status():
    """Get AI engine status."""
    return get_ai_engine().get_status()
