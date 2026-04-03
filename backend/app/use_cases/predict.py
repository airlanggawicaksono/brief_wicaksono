import json
from collections.abc import Generator

from app.core.technical_policy.cache import get_cached, put_cached
from app.services.extraction import ExtractionService
from app.services.predict import PredictService


class PredictUseCase:
    """One action: text → extraction → tool execution → response."""

    def __init__(self, extraction: ExtractionService, predict: PredictService):
        self.extraction = extraction
        self.predict = predict

    def run_stream(self, text: str) -> Generator[str]:
        cached = get_cached(text)
        if cached:
            yield f"event: cached\ndata: {json.dumps(cached)}\n\n"
            yield f"event: done\ndata: {{}}\n\n"
            return

        extraction = self.extraction.extract(text)
        yield f"event: extraction\ndata: {extraction.model_dump_json()}\n\n"

        tool_output = self.predict.execute(text)
        yield f"event: tool_result\ndata: {json.dumps(tool_output)}\n\n"

        result = {
            "input": text,
            "extraction": extraction.model_dump(),
            "tool_results": tool_output["tool_results"],
            "message": tool_output["message"],
        }
        put_cached(text, result)

        yield f"event: result\ndata: {json.dumps(result)}\n\n"
        yield f"event: done\ndata: {{}}\n\n"
