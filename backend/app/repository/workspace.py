import json

import redis

from app.config.settings import settings

WORKSPACE_PREFIX = "wpp:workspace:"
WORKSPACE_TTL = 60 * 60 * 24  # 24 hours — same as cache

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


class WorkspaceRepository:
    """Session-scoped scratch space for agent-generated datasets and images.

    Keys are session-scoped and expire after 24 hours so nothing persists
    beyond the session TTL. Each saved name is tracked in a Redis set so
    list() doesn't require a key scan.
    """

    def _data_key(self, session_id: str, name: str) -> str:
        return f"{WORKSPACE_PREFIX}{session_id}:{name}"

    def _index_key(self, session_id: str) -> str:
        return f"{WORKSPACE_PREFIX}{session_id}:__index__"

    def save(self, session_id: str, name: str, rows: list[dict]) -> None:
        r = _get_redis()
        r.set(self._data_key(session_id, name), json.dumps(rows, default=str), ex=WORKSPACE_TTL)
        r.sadd(self._index_key(session_id), name)
        r.expire(self._index_key(session_id), WORKSPACE_TTL)

    def load(self, session_id: str, name: str) -> list[dict] | None:
        r = _get_redis()
        raw = r.get(self._data_key(session_id, name))
        if raw is None:
            return None
        return json.loads(raw)

    def list(self, session_id: str) -> list[str]:
        r = _get_redis()
        return list(r.smembers(self._index_key(session_id)))

    def clear(self, session_id: str) -> None:
        r = _get_redis()
        names = r.smembers(self._index_key(session_id))
        keys = [self._data_key(session_id, name) for name in names]
        keys.append(self._index_key(session_id))
        if keys:
            r.delete(*keys)
