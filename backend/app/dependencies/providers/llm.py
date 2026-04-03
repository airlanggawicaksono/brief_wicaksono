from langchain_openai import ChatOpenAI

from app.core.config.settings import settings


class LLMProvider:
    """Replaceable LLM provider. Swap OpenAI for any provider here — nothing else changes."""

    def __init__(self):
        self._llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            temperature=0,
            streaming=True,
        )

    @property
    def llm(self) -> ChatOpenAI:
        return self._llm

    def with_structured_output(self, schema):
        return self._llm.with_structured_output(schema)

    def bind_tools(self, tools):
        return self._llm.bind_tools(tools)
