import json
from collections.abc import Generator

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config.settings import settings
from app.dto.predict import Entities, PredictResponse
from app.models.product import Product
from app.repository.product import ProductRepository

SYSTEM_PROMPT = """You extract intent and entities from natural language input.
Return ONLY valid JSON with this exact structure:
{
  "intent": "<string>",
  "entities": {
    "category": "<string or null>",
    "target": "<string or null>",
    "price_max": <integer or null>
  }
}

Common intents: product_search, product_detail, greeting, unknown
Do not include any text outside the JSON."""

llm = ChatOpenAI(
    api_key=settings.OPENAI_API_KEY,
    model=settings.OPENAI_MODEL,
    temperature=0,
    streaming=True,
)


class PredictService:
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo

    def predict_stream(self, text: str) -> Generator[str]:
        """Stream tokens via SSE, then emit the parsed result at the end."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=text),
        ]

        full_response = ""
        for chunk in llm.stream(messages):
            token = chunk.content
            if token:
                full_response += token
                yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"

        # parse final result
        try:
            data = json.loads(full_response)
            result = PredictResponse(
                intent=data.get("intent", "unknown"),
                entities=Entities(**data.get("entities", {})),
            )
        except (json.JSONDecodeError, Exception):
            result = PredictResponse(intent="unknown", entities=Entities())

        yield f"event: result\ndata: {result.model_dump_json()}\n\n"
        yield f"event: done\ndata: {{}}\n\n"

    def predict(self, text: str) -> PredictResponse:
        """Non-streaming predict for internal use (e.g. search)."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=text),
        ]
        response = llm.invoke(messages)
        raw = response.content.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return PredictResponse(intent="unknown", entities=Entities())

        return PredictResponse(
            intent=data.get("intent", "unknown"),
            entities=Entities(**data.get("entities", {})),
        )

    def search_products(self, entities: Entities) -> list[Product]:
        return self.product_repo.search(
            category=entities.category,
            target=entities.target,
            price_max=entities.price_max,
        )
