
import json
from typing import Dict, Optional

import httpx

from ...core.config import settings
from ...core.logging import logger
from .base import AIProvider


class GeminiProvider(AIProvider):
    """Google Gemini API provider - excellent free tier and speed."""
    
    name = "gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    # Free tier: 1500 requests/day, 32k context, fast responses
    FREE_MODEL = "gemini-1.5-flash"  # Fast, free
    PRO_MODEL = "gemini-1.5-pro"     # More capable, still free tier
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL or self.FREE_MODEL
    
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
        """Generate response using Gemini API."""
        if not self.is_available():
            raise ValueError("Gemini API key not configured")
        
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        
        # Combine system prompt with user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        payload = {
            "contents": [
                {
                    "parts": [{"text": full_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95,
                "topK": 40,
            },
            "safetySettings": [
                {
                    "category": cat,
                    "threshold": "BLOCK_NONE"  # Allow code generation
                }
                for cat in [
                    "HARM_CATEGORY_HARASSMENT",
                    "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "HARM_CATEGORY_DANGEROUS_CONTENT"
                ]
            ]
        }
        
        try:
            logger.info(f"Calling Gemini API with model {self.model}")
            
            with httpx.Client(timeout=settings.LLM_TIMEOUT) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract generated text from Gemini response
                # Response format: {"candidates": [{"content": {"parts": [{"text": "..."}], "role": "model"}}]}
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    content = candidate.get("content", {})
                    parts = content.get("parts", [])
                    
                    if parts and "text" in parts[0]:
                        text = parts[0]["text"]
                        logger.info(f"Gemini generated {len(text)} characters")
                        return text
                    else:
                        logger.error(f"No text in Gemini response parts: {parts}")
                        raise ValueError(f"No text in Gemini response")
                else:
                    logger.error(f"Unexpected Gemini response: {data}")
                    raise ValueError(f"No candidates in Gemini response")
                    
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"Gemini API error ({e.response.status_code}): {error_detail}")
            raise
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise
    
    def get_model_info(self) -> Dict:
        """Get provider information."""
        return {
            "provider": self.name,
            "model": self.model,
            "available": self.is_available(),
            "free_tier": "1500 requests/day",
            "context_window": "32k tokens",
            "speed": "Fast (optimized for speed)",
        }
    
    @staticmethod
    def list_models() -> Dict:
        """List available Gemini models."""
        return {
            "free": [
                "gemini-1.5-flash",      # Fast, efficient
                "gemini-1.5-flash-8b",   # Ultra fast, smaller
            ],
            "pro": [
                "gemini-1.5-pro",        # More capable, same free tier
            ],
            "info": {
                "free_tier": "1500 requests/day",
                "rate_limit": "15 requests/minute",
                "context": "Up to 1M tokens (flash), 2M tokens (pro)",
            }
        }
