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
        if event.type == EventType.ARTIFACT:
            return f"event: artifact\ndata: {json.dumps(event.data, default=str)}\n\n"
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
    def done() -> str:
        return "event: done\ndata: {}\n\n"


class ToolResultFormatter:
    """All formatting logic for tool execution results: compaction, artifact extraction, labels.

    Lives here (presentation layer) so steps.py stays pure orchestration.
    """

    @staticmethod
    def is_error(item) -> bool:
        return isinstance(item.data, dict) and "error" in item.data

    @staticmethod
    def compact_for_ui(item, *, is_error: bool = False) -> dict:
        """Compact tool output for the frontend.

        Error results get a flat {tool, args, error: true, message} shape.
        Schema results strip verbose column metadata down to a summary.
        """
        if is_error and isinstance(item.data, dict):
            error = item.data.get("error", {})
            msg = error.get("message", "Error") if isinstance(error, dict) else str(error)
            return {"tool": item.tool, "args": item.args, "error": True, "message": msg}

        if item.tool == "save_result":
            return {"tool": item.tool, "args": item.args, "saved": True}

        if item.tool in ("list_workspace", "run_python"):
            return {"tool": item.tool, "args": item.args}

        if item.tool != "lookup_schema" or not isinstance(item.data, dict):
            return item.model_dump(warnings=False)

        tables = item.data.get("tables")
        if not isinstance(tables, dict):
            return item.model_dump(warnings=False)

        compact_tables = [
            {
                "table": table_key,
                "column_count": meta.get("column_count"),
                "columns": meta.get("column_names"),
            }
            for table_key, meta in tables.items()
            if isinstance(meta, dict)
        ]
        return {
            "tool": item.tool,
            "args": item.args,
            "data": {"table_count": len(compact_tables), "tables": compact_tables},
        }

    @staticmethod
    def detail(item) -> str:
        if isinstance(item.data, dict) and "error" in item.data:
            error = item.data["error"]
            if isinstance(error, dict):
                return error.get("message", "Error")
            return str(error)
        if isinstance(item.data, dict) and "row_count" in item.data:
            return f"Returned {item.data['row_count']} row(s)."
        return "Complete."

