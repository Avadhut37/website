"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


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
