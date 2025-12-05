
from typing import List, Optional, Tuple
from enum import Enum

from ..core.logging import logger
from ..core.config import settings


class ProviderPriority(Enum):
    """Provider priority levels."""
    PRIMARY = 1    # Gemini - fast, free 1500/day
    SECONDARY = 2  # OpenRouter - good quality, limited free
    TERTIARY = 3   # Ollama - unlimited but slower
    FALLBACK = 4   # Templates - always works


class ModelRouter:
    """Intelligent routing to select best available AI provider."""
    
    def __init__(self, providers: List):
        self.providers = providers
        self.provider_stats = {}  # Track success/failure rates
        self._initialize_stats()
    
    def _initialize_stats(self):
        """Initialize provider statistics."""
        for provider in self.providers:
            self.provider_stats[provider.name] = {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "avg_time": 0.0,
                "consecutive_failures": 0,
            }
    
    def get_priority(self, provider_name: str) -> int:
        """Get priority level for provider."""
        priority_map = {
            "deepseek": ProviderPriority.PRIMARY.value,     # Best for reasoning
            "gemini": ProviderPriority.PRIMARY.value,        # Best for UI/text
            "groq": ProviderPriority.PRIMARY.value,          # Best for code
            "cerebras": ProviderPriority.SECONDARY.value,    # Alternative reasoning
            "openrouter": ProviderPriority.SECONDARY.value,  # Fallback
            "ollama": ProviderPriority.TERTIARY.value,       # Local fallback
        }
        return priority_map.get(provider_name.lower(), ProviderPriority.FALLBACK.value)
    
    def select_provider(self) -> Tuple[Optional[object], str]:
        """
        Intelligently select best provider based on:
        - Availability
        - Priority (speed/cost)
        - Recent success rate
        - Consecutive failures
        """
        available = [p for p in self.providers if p.is_available()]
        
        if not available:
            logger.warning("No AI providers available")
            return None, "No providers available"
        
        # Sort by priority and success rate
        def score_provider(provider):
            stats = self.provider_stats.get(provider.name, {})
            priority = self.get_priority(provider.name)
            
            # Circuit breaker: skip if too many consecutive failures
            if stats.get("consecutive_failures", 0) >= 3:
                logger.warning(f"Provider {provider.name} circuit broken (3+ failures)")
                return 999  # Very low priority
            
            # Calculate success rate
            attempts = stats.get("attempts", 0)
            if attempts > 0:
                success_rate = stats.get("successes", 0) / attempts
            else:
                success_rate = 1.0  # Assume success for untried providers
            
            # Lower score = better (priority 1 is best)
            # Penalize based on failure rate
            return priority + (1 - success_rate) * 2
        
        # Sort by score
        sorted_providers = sorted(available, key=score_provider)
        selected = sorted_providers[0]
        
        reason = f"Selected {selected.name} (priority {self.get_priority(selected.name)})"
        logger.info(reason)
        
        return selected, reason
    
    def record_success(self, provider_name: str, duration: float):
        """Record successful generation."""
        if provider_name not in self.provider_stats:
            return
        
        stats = self.provider_stats[provider_name]
        stats["attempts"] += 1
        stats["successes"] += 1
        stats["consecutive_failures"] = 0
        
        # Update average time (rolling average)
        prev_avg = stats["avg_time"]
        total = stats["successes"]
        stats["avg_time"] = (prev_avg * (total - 1) + duration) / total
        
        logger.info(
            f"Provider {provider_name}: success "
            f"({stats['successes']}/{stats['attempts']}, "
            f"avg {stats['avg_time']:.2f}s)"
        )
    
    def record_failure(self, provider_name: str, error: str):
        """Record failed generation."""
        if provider_name not in self.provider_stats:
            return
        
        stats = self.provider_stats[provider_name]
        stats["attempts"] += 1
        stats["failures"] += 1
        stats["consecutive_failures"] += 1
        
        logger.warning(
            f"Provider {provider_name}: failure "
            f"({stats['failures']}/{stats['attempts']}, "
            f"{stats['consecutive_failures']} consecutive) - {error}"
        )
    
    def get_stats(self) -> dict:
        """Get current provider statistics."""
        return {
            "providers": self.provider_stats,
            "total_attempts": sum(s["attempts"] for s in self.provider_stats.values()),
            "total_successes": sum(s["successes"] for s in self.provider_stats.values()),
        }
