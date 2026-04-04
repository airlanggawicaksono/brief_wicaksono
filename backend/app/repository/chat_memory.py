from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.core.config.settings import settings


class RedisChatMemory:
    """Session-scoped chat memory backed by LangChain Redis integration."""

    def _get_history(self, session_id: str):
        try:
            from langchain_redis import RedisChatMessageHistory
        except ImportError as exc:
            raise RuntimeError(
                "langchain-redis is required for Redis chat memory. "
                "Install dependency: langchain-redis"
            ) from exc

        return RedisChatMessageHistory(
            session_id=session_id,
            redis_url=settings.redis_url,
        )

    def load_messages(self, session_id: str, limit: int = 20) -> list[dict]:
        history = self._get_history(session_id)
        messages: list[BaseMessage] = history.messages
        if limit > 0:
            messages = messages[-limit:]

        result: list[dict] = []
        for message in messages:
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                continue

            if not isinstance(message.content, str):
                continue

            result.append({"role": role, "content": message.content})

        return result

    def append_turn(self, session_id: str, user_text: str, assistant_text: str) -> None:
        history = self._get_history(session_id)
        history.add_user_message(user_text)
        history.add_ai_message(assistant_text)
