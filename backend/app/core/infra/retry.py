import functools
import time

from loguru import logger


def retry(max_retries: int = 2, backoff: float = 1.0):
    """Decorator: retry on failure with exponential backoff."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        wait = backoff * (2 ** attempt)
                        logger.warning(f"{fn.__name__} attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                        time.sleep(wait)
            logger.error(f"{fn.__name__} all {max_retries + 1} attempts failed")
            raise last_error
        return wrapper
    return decorator
