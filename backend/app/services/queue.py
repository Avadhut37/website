"""Background job queue using Redis Queue (RQ)."""
import os
from typing import Any, Callable, Optional

from redis import Redis
from rq import Queue
from rq.job import Job

from ..core.config import settings
from ..core.logging import logger


class JobQueue:
    """
    Background job queue manager.
    
    Uses Redis Queue for production, falls back to sync execution in dev.
    """
    
    def __init__(self):
        self._redis: Optional[Redis] = None
        self._queue: Optional[Queue] = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis."""
        try:
            self._redis = Redis.from_url(settings.REDIS_URL)
            self._redis.ping()  # Test connection
            self._queue = Queue(connection=self._redis)
            logger.info("Connected to Redis for background jobs")
        except Exception as e:
            logger.warning(f"Redis not available, using sync execution: {e}")
            self._redis = None
            self._queue = None
    
    @property
    def is_available(self) -> bool:
        """Check if queue is available."""
        return self._queue is not None
    
    def enqueue(
        self,
        func: Callable,
        *args,
        job_timeout: int = 600,
        **kwargs
    ) -> Optional[Job]:
        """
        Enqueue a job for background execution.
        
        Falls back to sync execution if Redis is not available.
        """
        if self.is_available:
            try:
                job = self._queue.enqueue(
                    func,
                    *args,
                    job_timeout=job_timeout,
                    **kwargs
                )
                logger.info(f"Enqueued job {job.id} for {func.__name__}")
                return job
            except Exception as e:
                logger.error(f"Failed to enqueue job: {e}")
        
        # Fallback: execute synchronously
        logger.info(f"Executing {func.__name__} synchronously")
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Sync execution failed: {e}")
            raise
        
        return None
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        if not self.is_available:
            return None
        try:
            return Job.fetch(job_id, connection=self._redis)
        except Exception:
            return None
    
    def get_queue_status(self) -> dict:
        """Get queue status."""
        if not self.is_available:
            return {"available": False, "message": "Redis not connected"}
        
        return {
            "available": True,
            "queued": len(self._queue),
            "failed": self._queue.failed_job_registry.count,
            "finished": self._queue.finished_job_registry.count,
        }


# Singleton instance
_job_queue: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Get or create the job queue singleton."""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueue()
    return _job_queue
