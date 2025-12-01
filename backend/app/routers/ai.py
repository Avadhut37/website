"""AI generation endpoints."""
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..ai.engine import call_llm_and_generate, get_ai_engine
from ..ai.providers.openrouter import OpenRouterProvider
from ..core.rate_limit import limiter, RATE_LIMITS

router = APIRouter()


class SpecPayload(BaseModel):
    spec: dict[str, Any]


class GenerationResponse(BaseModel):
    files: dict[str, str]
    file_count: int
    provider: str = "unknown"


@router.post("/preview", response_model=GenerationResponse)
@limiter.limit(RATE_LIMITS["generation"])
def preview_generation(request: Request, payload: SpecPayload):
    """Preview code generation without saving to a project."""
    try:
        files = call_llm_and_generate(payload.spec)
        engine = get_ai_engine()
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
