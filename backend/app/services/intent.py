from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.business_policy.intent_policy import IntentPolicy
from app.core.prompts.extraction import EXTRACTION_PROMPT
from app.core.technical_policy.retry import retry
from app.dto.response import PredictResponse


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
            SystemMessage(content=EXTRACTION_PROMPT),
            HumanMessage(content=text),
        ]
        result = self._coerce_response(self.structured_llm.invoke(messages))
        result.intent = self.intent_policy.normalize(result.intent)
        return result

    def _coerce_response(self, value: object) -> PredictResponse:
        if isinstance(value, PredictResponse):
            return value

        if isinstance(value, dict):
            parsed = value.get("parsed")
            if parsed is not None:
                return PredictResponse.model_validate(parsed)
            return PredictResponse.model_validate(value)

        parsed_attr = getattr(value, "parsed", None)
        if parsed_attr is not None:
            return PredictResponse.model_validate(parsed_attr)

        return PredictResponse.model_validate(value)
