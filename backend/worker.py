"""RQ Worker script for processing background jobs."""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from redis import Redis
from rq import Worker, Queue, Connection

from app.core.config import settings
from app.core.logging import logger


def run_worker():
    """Start the RQ worker."""
    logger.info("Starting RQ worker...")
    
    redis_conn = Redis.from_url(settings.REDIS_URL)
    
    with Connection(redis_conn):
        worker = Worker(['default'])
        worker.work()


if __name__ == '__main__':
    run_worker()
