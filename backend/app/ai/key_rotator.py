"""API Key Rotation System - Scale to lakhs of users with multiple free keys."""
import os
from typing import List, Optional
from collections import defaultdict
import time

from ..core.logging import logger


class APIKeyRotator:
    """
    Rotates between multiple API keys to maximize free tier usage.
    
    For lakhs of users:
    - Gemini: 1500 req/day per key
    - OpenRouter: 50 req/day per key
    
    Example:
    - 10 Gemini keys = 15,000 free requests/day
    - 20 Gemini keys = 30,000 free requests/day
    - 100 Gemini keys = 150,000 free requests/day (1.5 lakh/day!)
    """
    
    def __init__(self, provider_name: str, keys: List[str]):
        self.provider_name = provider_name
        self.keys = [k for k in keys if k and k.strip()]  # Filter empty keys
        self.current_index = 0
        
        # Track usage per key
        self.usage = defaultdict(lambda: {
            "requests": 0,
            "failures": 0,
            "last_reset": time.time(),
            "blocked_until": 0,
        })
        
        # Rate limits (requests per day)
        self.limits = {
            "gemini": 1500,
            "openrouter": 50,
        }
        
        logger.info(f"🔄 Key rotation enabled for {provider_name}: {len(self.keys)} keys available")
    
    def get_next_key(self) -> Optional[str]:
        """Get next available API key using round-robin with health checks."""
        if not self.keys:
            return None
        
        current_time = time.time()
        attempts = 0
        
        # Try to find a healthy key
        while attempts < len(self.keys):
            key = self.keys[self.current_index]
            usage = self.usage[key]
            
            # Reset daily counter if 24 hours passed
            if current_time - usage["last_reset"] > 86400:  # 24 hours
                usage["requests"] = 0
                usage["failures"] = 0
                usage["last_reset"] = current_time
                usage["blocked_until"] = 0
            
            # Skip if blocked due to rate limit
            if current_time < usage["blocked_until"]:
                self.current_index = (self.current_index + 1) % len(self.keys)
                attempts += 1
                continue
            
            # Check if under rate limit
            limit = self.limits.get(self.provider_name.lower(), 1000)
            if usage["requests"] < limit:
                return key
            
            # Key exhausted, try next
            self.current_index = (self.current_index + 1) % len(self.keys)
            attempts += 1
        
        logger.warning(f"⚠️ All {self.provider_name} keys exhausted or blocked")
        return None
    
    def record_request(self, key: str, success: bool = True):
        """Record API request for usage tracking."""
        self.usage[key]["requests"] += 1
        
        if not success:
            self.usage[key]["failures"] += 1
            
            # Block key for 1 hour after 3 consecutive failures
            if self.usage[key]["failures"] >= 3:
                self.usage[key]["blocked_until"] = time.time() + 3600
                logger.warning(f"🚫 {self.provider_name} key blocked for 1 hour (too many failures)")
        else:
            # Reset failure counter on success
            self.usage[key]["failures"] = 0
        
        # Move to next key for load balancing
        self.current_index = (self.current_index + 1) % len(self.keys)
    
    def get_stats(self) -> dict:
        """Get usage statistics for all keys."""
        total_requests = sum(u["requests"] for u in self.usage.values())
        active_keys = sum(1 for k in self.keys if self.usage[k]["requests"] < self.limits.get(self.provider_name.lower(), 1000))
        
        return {
            "provider": self.provider_name,
            "total_keys": len(self.keys),
            "active_keys": active_keys,
            "total_requests": total_requests,
            "limit_per_key": self.limits.get(self.provider_name.lower(), "Unknown"),
            "total_capacity": len(self.keys) * self.limits.get(self.provider_name.lower(), 0),
        }


def load_keys_from_env(provider: str) -> List[str]:
    """
    Load API keys from environment variables.
    
    Supports multiple keys in format:
    GEMINI_API_KEY=key1
    GEMINI_API_KEY_2=key2
    GEMINI_API_KEY_3=key3
    ...
    
    Or comma-separated:
    GEMINI_API_KEYS=key1,key2,key3
    """
    keys = []
    
    # Try comma-separated format first
    multi_key = os.getenv(f"{provider.upper()}_API_KEYS", "")
    if multi_key:
        keys.extend([k.strip() for k in multi_key.split(",") if k.strip()])
    
    # Try numbered format (KEY_1, KEY_2, etc.)
    base_key = os.getenv(f"{provider.upper()}_API_KEY", "")
    if base_key:
        keys.append(base_key)
    
    # Check for numbered keys (up to 100)
    for i in range(2, 101):
        key = os.getenv(f"{provider.upper()}_API_KEY_{i}", "")
        if key:
            keys.append(key)
    
    # Remove duplicates
    keys = list(dict.fromkeys(keys))
    
    return keys


# Global rotators
_gemini_rotator: Optional[APIKeyRotator] = None
_openrouter_rotator: Optional[APIKeyRotator] = None


def get_gemini_rotator() -> Optional[APIKeyRotator]:
    """Get or create Gemini key rotator."""
    global _gemini_rotator
    if _gemini_rotator is None:
        keys = load_keys_from_env("GEMINI")
        if keys:
            _gemini_rotator = APIKeyRotator("gemini", keys)
    return _gemini_rotator


def get_openrouter_rotator() -> Optional[APIKeyRotator]:
    """Get or create OpenRouter key rotator."""
    global _openrouter_rotator
    if _openrouter_rotator is None:
        keys = load_keys_from_env("OPENROUTER")
        if keys:
            _openrouter_rotator = APIKeyRotator("openrouter", keys)
    return _openrouter_rotator
