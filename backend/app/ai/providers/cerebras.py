"""Cerebras AI Provider - FREE & Ultra-fast for reasoning/code."""
from typing import Dict, Optional

import httpx

from ...core.config import settings
from ...core.logging import logger
from .base import AIProvider


class CerebrasProvider(AIProvider):
    """
    Cerebras API provider - Ultra-fast inference, great for reasoning.
    
    FREE Tier:
    - ~500 requests/day (estimated)
    - Models: Llama 3.1 70B, Llama 3.1 8B
    - No credit card required
    
    Best for: Reasoning, planning, complex tasks
    Speed: Comparable to Groq (ultra-fast)
    
    Get API key: https://cloud.cerebras.ai
    """
    
    name = "cerebras"
    base_url = "https://api.cerebras.ai/v1"
    
    # Best FREE models (as of Dec 2025)
    MODELS = {
        "llama-3.3-70b": "Best quality (70B) - recommended",
        "llama3.1-8b": "Fast (8B) - good for simple tasks",
        "qwen-3-32b": "Qwen 3 32B - excellent reasoning",
    }
    
    DEFAULT_MODEL = "llama-3.3-70b"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or getattr(settings, 'CEREBRAS_API_KEY', None)
        self.model = model or getattr(settings, 'CEREBRAS_MODEL', None) or self.DEFAULT_MODEL
    
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
        """Generate response using Cerebras API (OpenAI-compatible)."""
        if not self.is_available():
            raise ValueError("Cerebras API key not configured")
        
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
            logger.info(f"Calling Cerebras API with model {self.model}")
            
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                logger.info(f"Cerebras generated {len(content)} characters")
                return content
                
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"Cerebras API error ({e.response.status_code}): {error_detail}")
            raise
        except Exception as e:
            logger.error(f"Cerebras error: {e}")
            raise
    
    def get_model_info(self) -> Dict:
        """Get provider information."""
        return {
            "provider": self.name,
            "model": self.model,
            "available": self.is_available(),
            "free_tier": "~500 requests/day",
            "best_for": "Reasoning, planning, complex tasks",
            "speed": "Ultra-fast (comparable to Groq)",
        }
    
    @staticmethod
    def list_models() -> Dict:
        """List available Cerebras models."""
        return {
            "models": [
                "llama3.1-70b",   # Best quality
                "llama3.1-8b",    # Faster
            ],
            "info": {
                "free_tier": "~500 requests/day",
                "signup": "https://cloud.cerebras.ai",
                "no_credit_card": True,
            }
        }
