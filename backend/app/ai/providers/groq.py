"""Groq AI Provider - FREE & FAST for code generation."""
from typing import Dict, Optional

import httpx

from ...core.config import settings
from ...core.logging import logger
from .base import AIProvider


class GroqProvider(AIProvider):
    """
    Groq API provider - Ultra-fast inference, great for code.
    
    FREE Tier:
    - 30 requests/minute
    - ~14,400 requests/day
    - Models: Llama 3.3 70B, Mixtral 8x7B
    
    Best for: Code generation, fast responses
    """
    
    name = "groq"
    base_url = "https://api.groq.com/openai/v1"
    
    # Best FREE models for coding
    MODELS = {
        "llama-3.3-70b-versatile": "Best quality (70B)",
        "llama-3.1-70b-versatile": "Great for code (70B)", 
        "mixtral-8x7b-32768": "Fast, good quality (32k context)",
        "llama-3.1-8b-instant": "Ultra-fast (8B)",
    }
    
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL or self.DEFAULT_MODEL
    
    def is_available(self) -> bool:
        """Check if provider is available."""
        return bool(self.api_key)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> str:
        """Generate response using Groq API (OpenAI-compatible)."""
        if not self.is_available():
            raise ValueError("Groq API key not configured")
        
        url = f"{self.base_url}/chat/completions"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            logger.info(f"Calling Groq API with model {self.model}")
            
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                
                logger.info(f"Groq generated {len(text)} characters")
                return text
                
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"Groq API error ({e.response.status_code}): {error_detail}")
            raise
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            raise
    
    def get_model_info(self) -> Dict:
        """Get provider information."""
        return {
            "provider": self.name,
            "model": self.model,
            "available": self.is_available(),
            "free_tier": "14,400 requests/day (30/min)",
            "best_for": "Code generation, fast inference",
            "speed": "Ultra-fast (fastest provider)",
        }
    
    @staticmethod
    def list_models() -> Dict:
        """List available Groq models."""
        return {
            "models": GroqProvider.MODELS,
            "recommended": "llama-3.3-70b-versatile",
            "info": {
                "free_tier": "30 req/min, ~14,400/day",
                "context": "Up to 128k tokens",
                "speed": "Fastest in industry",
            }
        }
