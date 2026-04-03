import hashlib
import json

import redis

from app.core.config.settings import settings

CACHE_PREFIX = "wpp:cache:"
HISTORY_KEY = "wpp:history:index"
CACHE_TTL = 60 * 60 * 24  # 24 hours


def _get_redis() -> redis.Redis:
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
    )


def _hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()


def get_cached(text: str) -> dict | None:
    r = _get_redis()
    key = CACHE_PREFIX + _hash(text)
    data = r.get(key)
    if data:
        return json.loads(data)
    return None


def put_cached(text: str, result: dict) -> None:
    r = _get_redis()
    key = CACHE_PREFIX + _hash(text)
    payload = json.dumps(result)
    r.set(key, payload, ex=CACHE_TTL)
    r.lpush(HISTORY_KEY, payload)
    r.ltrim(HISTORY_KEY, 0, 199)


def list_recent(limit: int = 50) -> list[dict]:
    r = _get_redis()
    items = r.lrange(HISTORY_KEY, 0, limit - 1)
    return [json.loads(item) for item in items]
