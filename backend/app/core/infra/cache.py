import hashlib
import json

import redis

from app.config.settings import settings

CACHE_PREFIX = "wpp:cache:"
CACHE_TTL = 60 * 60 * 24  # 24 hours

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )
    return _redis_client


def _hash(text: str, scope_key: str | None = None) -> str:
    namespace = (scope_key or "global").strip().lower()
    payload = f"{namespace}::{text.strip().lower()}"
    return hashlib.sha256(payload.encode()).hexdigest()


def get_cached(text: str, scope_key: str | None = None) -> dict | None:
    r = _get_redis()
    key = CACHE_PREFIX + _hash(text, scope_key=scope_key)
    data = r.get(key)
    if data:
        return json.loads(data)
    return None


def put_cached(text: str, result: dict, scope_key: str | None = None) -> None:
    r = _get_redis()
    key = CACHE_PREFIX + _hash(text, scope_key=scope_key)
    payload = json.dumps(result)
    r.set(key, payload, ex=CACHE_TTL)
