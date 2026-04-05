import json

from app.core.enums.event_type import EventType
from app.services.predict.dto import ProcessEvent, PredictResult


class SsePresenter:
    """Converts ProcessEvents and domain objects to SSE-formatted strings.

    Only this class knows about the `event: ...\\ndata: ...\\n\\n` wire format.
    """

    @staticmethod
    def render(event: ProcessEvent) -> str:
        """Route to the correct wire format based on event type."""
        if event.type == EventType.TOOL_START or event.type == EventType.TOOL_END:
            return SsePresenter._tool_event(event)
        if event.type == EventType.MESSAGE:
            return SsePresenter.message(event.detail)
        if event.type == EventType.EXTRACTION:
            return f"event: extraction\ndata: {json.dumps(event.data, default=str)}\n\n"
        return SsePresenter._process_event(event)

    @staticmethod
    def _process_event(event: ProcessEvent) -> str:
        payload = {
            "stage": event.stage,
            "title": event.title,
            "detail": event.detail,
            "timestamp": event.timestamp,
        }
        return f"event: process\ndata: {json.dumps(payload, default=str)}\n\n"

    @staticmethod
    def _tool_event(event: ProcessEvent) -> str:
        """Tool events send the tool data directly (frontend expects {tool, args, data})."""
        return f"event: {event.type}\ndata: {json.dumps(event.data, default=str)}\n\n"

    @staticmethod
    def message(text: str) -> str:
        return f"event: message\ndata: {json.dumps(text)}\n\n"

    @staticmethod
    def result(data: PredictResult) -> str:
        return f"event: result\ndata: {data.model_dump_json(warnings=False)}\n\n"

    @staticmethod
    def cached(data: PredictResult) -> str:
        return f"event: cached\ndata: {data.model_dump_json(warnings=False)}\n\n"

    @staticmethod
    def done() -> str:
        return "event: done\ndata: {}\n\n"
