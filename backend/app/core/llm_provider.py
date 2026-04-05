from langchain_core.language_models.chat_models import BaseChatModel

from app.config.settings import settings

SUPPORTED_LLM_PROVIDERS = ("openai", "claude", "gemini")


def _create_openai_provider() -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        temperature=0,
        streaming=True,
    )


def _create_claude_provider() -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        model=settings.ANTHROPIC_MODEL,
        temperature=0,
        streaming=True,
    )


def _create_gemini_provider() -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        google_api_key=settings.GOOGLE_API_KEY,
        model=settings.GOOGLE_MODEL,
        temperature=0,
        streaming=True,
    )


def create_llm_provider() -> BaseChatModel:
    provider = settings.LLM_PROVIDER.strip().lower()

    if provider == "openai":
        return _create_openai_provider()
    if provider == "claude":
        return _create_claude_provider()
    if provider == "gemini":
        return _create_gemini_provider()

    raise ValueError(
        f"Unknown LLM_PROVIDER '{settings.LLM_PROVIDER}'. "
        f"Supported values: {SUPPORTED_LLM_PROVIDERS}"
    )
