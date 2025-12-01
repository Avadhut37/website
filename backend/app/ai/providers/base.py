"""Base AI provider interface."""
from abc import ABC, abstractmethod
from typing import Dict, Optional


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    name: str = "base"
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate a response from the AI model.
        
        Args:
            prompt: The input prompt
            **kwargs: Provider-specific options
            
        Returns:
            Generated text or None if failed
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and available."""
        pass
    
    def get_model_info(self) -> Dict[str, str]:
        """Return information about the provider and model."""
        return {
            "provider": self.name,
            "available": self.is_available()
        }
