"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List, Dict, Literal
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator, validator


# ============ Auth Schemas ============

class UserRegister(BaseModel):
    """User registration input."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """User login input."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """User response (without sensitive data)."""
    id: int
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ============ Project Schemas ============

class ProjectCreate(BaseModel):
    """Project creation input."""
    name: str = Field(..., min_length=1, max_length=100)
    spec: str = Field(..., min_length=1, max_length=50000)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Project name cannot be empty")
        # Sanitize for filesystem
        forbidden = '<>:"/\\|?*'
        for char in forbidden:
            v = v.replace(char, "_")
        return v


class ProjectResponse(BaseModel):
    """Project response."""
    id: int
    name: str
    spec: str
    status: str
    owner_id: int
    created_at: datetime
    updated_at: datetime
    output_path: Optional[str] = None

    model_config = {"from_attributes": True}


class ProjectCreateResponse(BaseModel):
    """Response after project creation."""
    id: int
    status: str
    message: str = "Project generation started"


class ProjectListResponse(BaseModel):
    """Paginated project list response."""
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============ AI Schemas ============

class SpecPayload(BaseModel):
    """AI generation spec input."""
    spec: dict


class GenerationPreviewResponse(BaseModel):
    """AI generation preview response."""
    files: dict[str, str]
    file_count: int


# ============ Generic Schemas ============

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str

class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
    code: Optional[str] = None


# ============ PHASE 1: Manifest Schemas ============


class AppType(str, Enum):
    """Supported application types."""
    CRUD = "crud"
    ECOMMERCE = "ecommerce"
    DASHBOARD = "dashboard"
    SOCIAL = "social"
    TODO = "todo"
    BLOG = "blog"
    AUTH = "auth"
    BOOKING = "booking"
    API = "api"


class TechStack(BaseModel):
    """Technology stack specification."""
    backend: str = Field(default="FastAPI + Pydantic", description="Backend framework")
    frontend: str = Field(default="React 18 + Vite", description="Frontend framework")
    styling: str = Field(default="Tailwind CSS", description="CSS framework")
    database: Optional[str] = Field(default=None, description="Database (optional)")
    auth: Optional[str] = Field(default=None, description="Auth provider (optional)")


class DataModel(BaseModel):
    """Data model specification."""
    name: str = Field(description="Model name (e.g., User, Product)")
    fields: Dict[str, str] = Field(description="Field name -> type mapping")
    relationships: Optional[List[str]] = Field(default=[], description="Relationships to other models")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v[0].isupper():
            raise ValueError("Model name must start with uppercase letter")
        return v


class APIEndpoint(BaseModel):
    """API endpoint specification."""
    path: str = Field(description="Endpoint path (e.g., /items)")
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(description="HTTP method")
    description: str = Field(description="What this endpoint does")
    request_model: Optional[str] = Field(default=None, description="Request body model")
    response_model: str = Field(description="Response model")
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v):
        if not v.startswith('/'):
            return f"/{v}"
        return v


class FileSpec(BaseModel):
    """File specification."""
    path: str = Field(description="Relative file path")
    description: str = Field(description="What this file contains")
    dependencies: List[str] = Field(default=[], description="Files this depends on")


class ProjectManifest(BaseModel):
    """
    Structured project manifest - output of CORE agent.
    
    This is the single source of truth for project generation.
    All downstream agents use this manifest to generate code.
    """
    
    # Analysis
    analysis: str = Field(
        description="Brief requirement analysis (2-3 sentences)"
    )
    
    # Classification
    app_type: AppType = Field(
        description="Detected application type"
    )
    
    # Features
    features: List[str] = Field(
        min_length=1,
        description="List of features to implement"
    )
    
    # Tech Stack
    tech_stack: TechStack = Field(
        default_factory=TechStack,
        description="Technology stack"
    )
    
    # Architecture
    models: List[DataModel] = Field(
        default=[],
        description="Data models to create"
    )
    
    endpoints: List[APIEndpoint] = Field(
        default=[],
        description="API endpoints to implement"
    )
    
    # Files
    files_to_generate: List[FileSpec] = Field(
        description="Exact files to create with descriptions"
    )
    
    # Integrations
    integrations: List[str] = Field(
        default=[],
        description="Third-party integrations (supabase, stripe, auth0, etc.)"
    )
    
    # Agents
    agents_needed: List[Literal["ARCH", "BACKEND", "UIX", "DEBUG", "QUALITY", "TEST"]] = Field(
        description="Which specialist agents to activate"
    )
    
    # Priority
    priority: str = Field(
        description="What to build first (MVP focus)"
    )
    
    @field_validator('features')
    @classmethod
    def validate_features(cls, v):
        if not v:
            raise ValueError("At least one feature must be specified")
        return v
    
    @field_validator('files_to_generate')
    @classmethod
    def validate_files(cls, v):
        required_files = [
            "backend/main.py",
            "backend/requirements.txt",
            "frontend/src/App.jsx",
            "frontend/package.json"
        ]
        
        file_paths = [f.path for f in v]
        missing = [f for f in required_files if f not in file_paths]
        
        if missing:
            raise ValueError(f"Missing required files: {missing}")
        
        return v


class ArchitectureSpec(BaseModel):
    """
    Architecture specification - output of ARCH agent.
    
    Provides detailed design decisions and structure.
    """
    
    design_decisions: List[str] = Field(
        description="Key architecture decisions made"
    )
    
    endpoints: List[APIEndpoint] = Field(
        description="Complete API specification"
    )
    
    models: List[DataModel] = Field(
        description="Complete data model specification"
    )
    
    file_structure: Dict[str, str] = Field(
        description="File path -> purpose mapping"
    )
    
    scalability_notes: Optional[str] = Field(
        default=None,
        description="Notes on how this scales"
    )


# ============ Helper Functions ============


def validate_manifest(data: dict) -> ProjectManifest:
    """
    Validate and parse a project manifest.
    
    Args:
        data: Raw dict from LLM
        
    Returns:
        Validated ProjectManifest
        
    Raises:
        ValidationError: If manifest is invalid
    """
    return ProjectManifest(**data)


def create_default_manifest(project_name: str, description: str) -> ProjectManifest:
    """Create a default manifest for fallback."""
    return ProjectManifest(
        analysis=f"Building a basic {project_name} application",
        app_type=AppType.CRUD,
        features=["CRUD operations", "REST API", "React UI"],
        models=[
            DataModel(
                name="Item",
                fields={"id": "int", "title": "str", "created_at": "datetime"}
            )
        ],
        endpoints=[
            APIEndpoint(
                path="/items",
                method="GET",
                description="List all items",
                response_model="List[Item]"
            ),
            APIEndpoint(
                path="/items",
                method="POST",
                description="Create item",
                request_model="ItemCreate",
                response_model="Item"
            )
        ],
        files_to_generate=[
            FileSpec(path="backend/main.py", description="FastAPI app"),
            FileSpec(path="backend/requirements.txt", description="Dependencies"),
            FileSpec(path="frontend/src/App.jsx", description="Main React component"),
            FileSpec(path="frontend/package.json", description="NPM config"),
            FileSpec(path="frontend/index.html", description="HTML entry"),
            FileSpec(path="frontend/vite.config.js", description="Vite config"),
            FileSpec(path="frontend/src/main.jsx", description="React entry"),
            FileSpec(path="README.md", description="Documentation")
        ],
        agents_needed=["ARCH", "BACKEND", "UIX"],
        priority="Build basic CRUD first"
    )
    code: Optional[str] = None
