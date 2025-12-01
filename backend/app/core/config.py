"""Application configuration with validation."""
import os
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # App
    APP_NAME: str = "iStudiox"
    APP_VERSION: str = "0.1.0"
    APP_URL: str = "http://localhost:8000"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-USE-SECRETS"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/db.sqlite"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # AI Providers
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"  # Best for UI/UX text
    
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"  # Best for code (fastest)
    
    CEREBRAS_API_KEY: Optional[str] = None
    CEREBRAS_MODEL: str = "llama3.1-70b"  # Best for reasoning (ultra-fast)
    
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "meta-llama/llama-3.2-3b-instruct:free"
    OPENROUTER_USE_FREE_ONLY: bool = True
    
    LLM_TIMEOUT: int = 120
    LLM_MAX_TOKENS: int = 8192
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_GENERATION: str = "5/minute"  # Stricter for AI generation
    
    # Generation
    MAX_SPEC_LENGTH: int = 50000
    MAX_PROJECT_NAME_LENGTH: int = 100
    WORK_DIR: str = "./work"
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        return v
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
