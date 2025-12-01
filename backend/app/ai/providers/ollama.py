"""Ollama local AI provider."""
import os
import subprocess
from typing import Optional

import httpx

from ...core.logging import logger
from .base import AIProvider


class OllamaProvider(AIProvider):
    """Local Ollama provider for running models locally."""
    
    name = "ollama"
    
    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5-coder")
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._available: Optional[bool] = None
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        if self._available is not None:
            return self._available
        
        try:
            # Check if ollama CLI exists
            result = subprocess.run(
                ["which", "ollama"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                self._available = False
                return False
            
            # Check if Ollama server is running
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            self._available = response.status_code == 200
            return self._available
        except Exception:
            self._available = False
            return False
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """Generate using Ollama API."""
        if not self.is_available():
            logger.warning("Ollama not available")
            return None
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("response", "")
                    logger.info(f"Ollama generated {len(content)} chars using {self.model}")
                    return content
                else:
                    logger.error(f"Ollama error: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return None
    
    def get_model_info(self) -> dict:
        """Return provider information."""
        return {
            "provider": self.name,
            "model": self.model,
            "base_url": self.base_url,
            "available": self.is_available(),
        }
