"""Rate limiting middleware."""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_WINDOW}seconds"],
    enabled=settings.RATE_LIMIT_ENABLED,
)


def get_rate_limit_exceeded_handler():
    """Get the rate limit exceeded handler."""
    return _rate_limit_exceeded_handler


# Rate limit decorators for different endpoints
RATE_LIMITS = {
    "default": f"{settings.RATE_LIMIT_REQUESTS}/minute",
    "auth": "10/minute",  # Strict for auth endpoints
    "generation": settings.RATE_LIMIT_GENERATION,  # Very strict for AI
    "download": "30/minute",
}
