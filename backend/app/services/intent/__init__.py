from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.infra.retry import retry
from app.policy.intent import IntentPolicy
from app.prompts.intent_detection import INTENT_DETECTION_PROMPT
from app.services.intent.dto import PredictResponse


class IntentService:
    """Detects intent and extracts entities from natural language input."""

    def __init__(self, provider: BaseChatModel, intent_policy: IntentPolicy):
        try:
            self.structured_llm = provider.with_structured_output(
                PredictResponse,
                include_raw=False,
            )
        except TypeError:
            self.structured_llm = provider.with_structured_output(PredictResponse)
        self.intent_policy = intent_policy

    @retry()
    def detect(self, text: str) -> PredictResponse:
        messages = [
            SystemMessage(content=INTENT_DETECTION_PROMPT),
            HumanMessage(content=text),
        ]
        result = self._coerce_response(self.structured_llm.invoke(messages))
        result.intent = self.intent_policy.normalize(result.intent)
        return result

    def _coerce_response(self, value: object) -> PredictResponse:
        """Extract PredictResponse from LangChain structured output.

        Always reconstructs a fresh PredictResponse to strip any
        provider-specific serialization metadata (e.g. LangChain's
        'parsed' wrapper) that causes Pydantic serializer warnings.
        """
        raw = value

        if isinstance(raw, dict):
            raw = raw.get("parsed", raw)
        elif not isinstance(raw, PredictResponse):
            raw = getattr(raw, "parsed", raw)

        if isinstance(raw, PredictResponse):
            return PredictResponse(intent=raw.intent, entities=raw.entities)

        return PredictResponse.model_validate(raw)
