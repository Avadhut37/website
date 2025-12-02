"""OpenRouter AI provider - access to multiple free and paid models."""
from typing import Dict, List, Optional

import httpx

from ...core.config import settings
from ...core.logging import logger
from .base import AIProvider


# Free models available on OpenRouter (as of 2024)
FREE_MODELS = [
    "meta-llama/llama-3.2-3b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "qwen/qwen-2-7b-instruct:free",
    "huggingfaceh4/zephyr-7b-beta:free",
]

# Higher quality models (paid but cheap)
QUALITY_MODELS = [
    "anthropic/claude-3-haiku",
    "openai/gpt-4o-mini",
    "google/gemini-flash-1.5",
    "meta-llama/llama-3.1-70b-instruct",
]


class OpenRouterProvider(AIProvider):
    """OpenRouter API provider for accessing multiple AI models."""
    
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        use_free_only: bool = True,
    ):
        # Use settings for API key
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.use_free_only = use_free_only
        
        # Select model based on configuration
        if model:
            self.model = model
        elif settings.OPENROUTER_MODEL:
            self.model = settings.OPENROUTER_MODEL
        elif use_free_only:
            self.model = FREE_MODELS[0]
        else:
            self.model = QUALITY_MODELS[0]
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": settings.APP_URL,
            "X-Title": settings.APP_NAME,
            "Content-Type": "application/json",
        }
    
    def is_available(self) -> bool:
        """Check if OpenRouter is configured."""
        return bool(self.api_key)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> Optional[str]:
        """Generate response using OpenRouter API (async)."""
        if not self.is_available():
            logger.warning("OpenRouter API key not configured")
            return None
        
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
        
        try:
            logger.info(f"Calling OpenRouter API with model {self.model}")
            
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info(f"OpenRouter generated {len(content)} chars using {self.model}")
                    return content
                else:
                    error_msg = response.text
                    logger.error(f"OpenRouter API error ({response.status_code}): {error_msg}")
                    
                    # Try fallback to a different free model
                    if self.use_free_only and self.model in FREE_MODELS:
                        return await self._try_fallback_models(messages, max_tokens, temperature)
                    
                    return None
                    
        except httpx.TimeoutException:
            logger.error("OpenRouter request timed out")
            return None
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            return None
    
    async def _try_fallback_models(
        self,
        messages: List[Dict],
        max_tokens: int,
        temperature: float
    ) -> Optional[str]:
        """Try alternative free models if the primary fails."""
        for model in FREE_MODELS:
            if model == self.model:
                continue
            
            logger.info(f"Trying fallback model: {model}")
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json=payload,
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]
                        logger.info(f"Fallback model {model} succeeded")
                        return content
            except Exception as e:
                logger.warning(f"Fallback model {model} failed: {e}")
                continue
        
        return None
    
    def get_model_info(self) -> Dict:
        """Return provider information."""
        return {
            "provider": self.name,
            "model": self.model,
            "available": self.is_available(),
            "free_models": FREE_MODELS,
            "quality_models": QUALITY_MODELS,
        }
    
    @classmethod
    def list_models(cls) -> Dict[str, List[str]]:
        """List available models."""
        return {
            "free": FREE_MODELS,
            "paid": QUALITY_MODELS,
        }
