"""iStudiox Backend API."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlmodel import SQLModel

from .core.config import settings
from .core.logging import logger
from .core.rate_limit import limiter, get_rate_limit_exceeded_handler
from .database import engine
from .routers import ai, auth, projects


def create_db_and_tables() -> None:
    """Initialize database tables."""
    SQLModel.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    create_db_and_tables()
    logger.info("Database initialized")
    
    # Log AI provider status
    from .ai.engine import get_ai_engine
    engine_status = get_ai_engine().get_status()
    logger.info(f"AI Engine: {len(engine_status['providers'])} providers available")
    
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered application builder API",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else "/api/docs",
    redoc_url="/redoc" if settings.DEBUG else "/api/redoc",
    openapi_url="/openapi.json" if settings.DEBUG else "/api/openapi.json",
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, get_rate_limit_exceeded_handler())

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# API v1 routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI"])

# Legacy routes (for backward compatibility)
app.include_router(auth.router, prefix="/auth", tags=["Authentication (Legacy)"], include_in_schema=False)
app.include_router(projects.router, prefix="/projects", tags=["Projects (Legacy)"], include_in_schema=False)
app.include_router(ai.router, prefix="/ai", tags=["AI (Legacy)"], include_in_schema=False)


@app.get("/", tags=["Health"])
@limiter.limit("60/minute")
def read_root(request: Request):
    """API root endpoint."""
    return {
        "message": f"{settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "api_version": "v1",
        "endpoints": {
            "auth": "/api/v1/auth",
            "projects": "/api/v1/projects",
            "ai": "/api/v1/ai",
            "docs": "/api/docs" if not settings.DEBUG else "/docs",
            "health": "/health",
        }
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/api/v1/status", tags=["Health"])
def api_status():
    """Detailed API status including AI providers."""
    from .ai.engine import get_ai_engine
    engine = get_ai_engine()
    
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "ai": engine.get_status(),
        "rate_limiting": settings.RATE_LIMIT_ENABLED,
    }
