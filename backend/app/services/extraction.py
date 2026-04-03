from langchain_core.messages import SystemMessage, HumanMessage

from app.core.technical_policy.retry import retry
from app.dependencies.providers.llm import LLMProvider
from app.dependencies.prompts.extraction import EXTRACTION_PROMPT
from app.dependencies.prompts.clarification import DOMAIN_CLARIFICATION_PROMPT
from app.dto.predict import PredictResponse


class ExtractionService:
    """Reusable: text → intent + entities via structured output."""

    def __init__(self, provider: LLMProvider):
        self.structured_llm = provider.with_structured_output(PredictResponse)

    @retry()
    def extract(self, text: str) -> PredictResponse:
        messages = [
            SystemMessage(content=EXTRACTION_PROMPT),
            HumanMessage(content=text),
        ]
        result = self.structured_llm.invoke(messages)

        if result.intent == "unknown":
            clarification = DOMAIN_CLARIFICATION_PROMPT.format(text=text)
            return self.structured_llm.invoke([SystemMessage(content=clarification)])

        return result
