"""Structured logging configuration."""
import logging
import sys
from typing import Any

from .config import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Simple format for dev, JSON for production
        if settings.DEBUG:
            return f"[{log_data['timestamp']}] {log_data['level']}: {log_data['message']}"
        else:
            import json
            return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """Configure application logging."""
    logger = logging.getLogger("istudiox")
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    
    return logger


logger = setup_logging()


def log_with_context(level: str, message: str, **kwargs: Any) -> None:
    """Log a message with additional context."""
    extra = {"extra": kwargs} if kwargs else {}
    getattr(logger, level.lower())(message, extra=extra)
