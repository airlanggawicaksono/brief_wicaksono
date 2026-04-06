import warnings

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.infra.retry import retry
from app.policy.intent import IntentPolicy
from app.prompts.intent_detection import INTENT_DETECTION_PROMPT
from app.repository.chat_memory import ChatMessage
from app.services.intent.dto import IntentExtraction


class IntentService:
    """Detects intent and extracts entities from natural language input."""

    def __init__(self, provider: BaseChatModel, intent_policy: IntentPolicy):
        try:
            self.structured_llm = provider.with_structured_output(
                IntentExtraction,
                include_raw=False,
                method="function_calling",
            )
        except TypeError:
            self.structured_llm = provider.with_structured_output(IntentExtraction)
        self.intent_policy = intent_policy

    @retry()
    def detect(self, text: str, history: list[ChatMessage] | None = None) -> IntentExtraction:
        messages: list = [SystemMessage(content=INTENT_DETECTION_PROMPT)]

        # include recent history so short follow-ups ("sure", "yes", "ok") are
        # classified in context rather than in isolation
        for entry in (history or [])[-6:]:
            if entry["role"] == "user":
                messages.append(HumanMessage(content=entry["content"]))
            elif entry["role"] == "assistant":
                messages.append(AIMessage(content=entry["content"]))

        messages.append(HumanMessage(content=text))

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Pydantic serializer warnings")
            raw = self.structured_llm.invoke(messages)
        result = self._coerce_response(raw)
        result.intent = self.intent_policy.normalize(result.intent)
        return result

    def _coerce_response(self, value: object) -> IntentExtraction:
        """Extract IntentExtraction from LangChain structured output.

        Always reconstructs a fresh IntentExtraction to strip any
        provider-specific serialization metadata (e.g. LangChain's
        'parsed' wrapper) that causes Pydantic serializer warnings.
        """
        raw = value

        if isinstance(raw, dict):
            raw = raw.get("parsed", raw)
        elif not isinstance(raw, IntentExtraction):
            raw = getattr(raw, "parsed", raw)

        if isinstance(raw, IntentExtraction):
            return IntentExtraction(intent=raw.intent, entities=raw.entities, language=raw.language)

        return IntentExtraction.model_validate(raw)
