"""DeepSeek AI Provider - FREE & excellent for reasoning/coding."""
from typing import Dict, Optional

import httpx

from ...core.config import settings
from ...core.logging import logger
from .base import AIProvider


class DeepSeekProvider(AIProvider):
    """
    DeepSeek API provider - Excellent for reasoning and complex code.
    
    FREE Tier:
    - Very generous free credits
    - DeepSeek-V3 and DeepSeek-R1 models
    
    Best for: Complex reasoning, architecture planning, debugging
    """
    
    name = "deepseek"
    base_url = "https://api.deepseek.com/v1"
    
    # Best models
    MODELS = {
        "deepseek-chat": "General purpose, fast (V3)",
        "deepseek-coder": "Specialized for coding",
        "deepseek-reasoner": "Best for complex reasoning (R1)",
    }
    
    DEFAULT_MODEL = "deepseek-chat"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        # Try DEEPSEEK_API_KEY first, fallback to OPENROUTER_API_KEY
        import os
        self.api_key = (
            api_key or 
            os.getenv("DEEPSEEK_API_KEY") or
            os.getenv("OPENROUTER_API_KEY")
        )
        self.model = model or self.DEFAULT_MODEL
    
    def is_available(self) -> bool:
        """Check if provider is available."""
        return bool(self.api_key)
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> str:
        """Generate response using DeepSeek API (OpenAI-compatible)."""
        if not self.is_available():
            raise ValueError("DeepSeek API key not configured")
        
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
            logger.info(f"Calling DeepSeek API with model {self.model}")
            
            with httpx.Client(timeout=settings.LLM_TIMEOUT) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                
                logger.info(f"DeepSeek generated {len(text)} characters")
                return text
                
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"DeepSeek API error ({e.response.status_code}): {error_detail}")
            raise
        except Exception as e:
            logger.error(f"DeepSeek generation failed: {e}")
            raise
    
    def get_model_info(self) -> Dict:
        """Get provider information."""
        return {
            "provider": self.name,
            "model": self.model,
            "available": self.is_available(),
            "free_tier": "Generous free credits",
            "best_for": "Reasoning, debugging, architecture",
            "speed": "Fast",
        }
    
    @staticmethod
    def list_models() -> Dict:
        """List available DeepSeek models."""
        return {
            "models": DeepSeekProvider.MODELS,
            "recommended": "deepseek-chat",
            "info": {
                "free_tier": "Free credits on signup",
                "context": "Up to 64k tokens",
                "specialty": "Reasoning & code",
            }
        }
