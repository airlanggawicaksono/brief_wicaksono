from collections.abc import Generator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.enums.intents import Intent
from app.repository.chat_memory import ChatMessage
from app.repository.workspace import WorkspaceRepository
from app.policy.intent import IntentPolicy
from app.core.enums.event_type import Stage, EventType
from app.prompts.clarification import CLARIFICATION_PROMPT
from app.prompts.general import GENERAL_PROMPT
from app.services.agent import AgentService
from app.services.agent.dto import ToolExecution
from app.services.intent import IntentService
from app.services.intent.dto import IntentExtraction
from app.services.predict.dto import (
    AgentStepOutput,
    ProcessEvent,
    RequestContext,
    StepResult,
)


class IntentStep:
    """Detect intent from user text."""

    name = "intent_detection"

    def __init__(self, intent_service: IntentService, intent_policy: IntentPolicy):
        self.intent_service = intent_service
        self.intent_policy = intent_policy

    def run(self, ctx: RequestContext) -> StepResult[IntentExtraction]:
        events: list[ProcessEvent] = [
            ProcessEvent(
                type=EventType.PROCESS,
                stage=Stage.RECEIVED_INPUT,
                title="Received input",
                detail="Starting intent detection.",
            ),
        ]

        try:
            extraction = self.intent_service.detect(ctx.text, history=ctx.history)
        except Exception as exc:
            events.append(
                ProcessEvent(
                    type=EventType.ERROR,
                    stage=Stage.FAILED,
                    title="Intent detection failed",
                    detail=str(exc),
                )
            )
            return StepResult(ok=False, events=events, error={"message": str(exc)})

        events.append(
            ProcessEvent(
                type=EventType.EXTRACTION,
                stage=Stage.INTENT_DETECTED,
                title="Intent detected",
                detail=extraction.intent,
                data=extraction.model_dump(warnings=False),
            )
        )
        return StepResult(ok=True, output=extraction, events=events)


class AgentStep:
    """Run the agent tool loop for data queries, streaming events as they happen."""

    name = "agent_execution"

    def __init__(
        self,
        agent_service: AgentService,
        workspace_repo: WorkspaceRepository,
        session_id: str,
    ):
        self.agent_service = agent_service
        self.workspace_repo = workspace_repo
        self.session_id = session_id

    def stream(
        self, extraction: IntentExtraction, ctx: RequestContext
    ) -> Generator[ProcessEvent | AgentStepOutput]:
        """Yields ProcessEvents live as tools execute, then yields a final dict output."""
        yield ProcessEvent(
            type=EventType.PROCESS,
            stage=Stage.AGENT_STARTED,
            title="Agent started",
            detail="Selecting tools.",
        )

        from app.services.predict.dto import Artifact

        tool_results: list[ToolExecution] = []
        artifacts: list[Artifact] = []
        message = ""

        entities = extraction.entities if isinstance(extraction.entities, dict) else None
        for item in self.agent_service.execute(
            ctx.text, ctx.history, intent=extraction.intent, entities=entities
        ):
            if isinstance(item, ToolExecution):
                if item.data is None:
                    yield ProcessEvent(
                        type=EventType.TOOL_START,
                        stage=Stage.TOOL_STARTED,
                        title=f"Running {item.tool}",
                        detail=str(item.args),
                        data=item.model_dump(warnings=False),
                    )
                else:
                    is_error = _is_tool_error(item)
                    if not is_error:
                        tool_results.append(item)
                    yield ProcessEvent(
                        type=EventType.TOOL_END,
                        stage=Stage.TOOL_FINISHED,
                        title=f"{item.tool} finished",
                        detail=_tool_detail(item),
                        data=_compact_for_ui(item, is_error=is_error),
                    )
                    artifact_data = _extract_artifact(item, self.workspace_repo, self.session_id)
                    if artifact_data:
                        artifact = Artifact(**artifact_data)
                        artifacts.append(artifact)
                        yield ProcessEvent(
                            type=EventType.ARTIFACT,
                            stage=Stage.ARTIFACT_READY,
                            title=_artifact_title(artifact_data),
                            data=artifact.model_dump(warnings=False),
                        )
            elif isinstance(item, str):
                message = item
                yield ProcessEvent(
                    type=EventType.MESSAGE,
                    stage=Stage.RESPONSE_READY,
                    title="Response",
                    detail=message,
                )

        yield AgentStepOutput(tool_results=tool_results, message=message, artifacts=artifacts)


class DirectResponseStep:
    """Direct LLM response for non-data intents (general, clarification)."""

    name = "direct_response"

    def __init__(self, provider: BaseChatModel):
        self.provider = provider

    def run(self, extraction: IntentExtraction, ctx: RequestContext) -> StepResult[str]:
        events: list[ProcessEvent] = [
            ProcessEvent(
                type=EventType.PROCESS,
                stage=Stage.DIRECT_RESPONSE,
                title="Direct response",
                detail="No tool execution needed.",
            ),
        ]

        message = self._invoke_llm(ctx.text, extraction.intent, ctx.history)

        events.append(
            ProcessEvent(
                type=EventType.MESSAGE,
                stage=Stage.RESPONSE_READY,
                title="Response",
                detail=message,
            )
        )
        return StepResult(ok=True, output=message, events=events)

    def _invoke_llm(self, text: str, intent: str, history: list[ChatMessage]) -> str:
        system_content = CLARIFICATION_PROMPT if intent == Intent.CLARIFICATION else GENERAL_PROMPT
        messages: list = [SystemMessage(content=system_content)]

        for entry in history or []:
            if entry["role"] == "user":
                messages.append(HumanMessage(content=entry["content"]))
            elif entry["role"] == "assistant":
                messages.append(AIMessage(content=entry["content"]))

        messages.append(HumanMessage(content=text))
        response = self.provider.invoke(messages)
        content = _content_to_text(response.content)
        if content:
            return content
        return "Could you clarify what you need about products, audiences, campaigns, or performance?"


def _is_tool_error(item: ToolExecution) -> bool:
    """Check if a tool execution result contains an error."""
    return isinstance(item.data, dict) and "error" in item.data


def _compact_for_ui(item: ToolExecution, *, is_error: bool = False) -> dict:
    """Compact tool output for the frontend.

    Error results get a flat {tool, args, error: true, message: "..."} shape
    so the frontend can show a simple indicator instead of rendering a table.
    """
    if is_error and isinstance(item.data, dict):
        error = item.data.get("error", {})
        msg = error.get("message", "Error") if isinstance(error, dict) else str(error)
        return {
            "tool": item.tool,
            "args": item.args,
            "error": True,
            "message": msg,
        }

    if item.tool == "save_result":
        return {"tool": item.tool, "args": item.args, "saved": True}

    if item.tool in ("list_workspace", "run_python"):
        return {"tool": item.tool, "args": item.args}

    if item.tool != "lookup_schema" or not isinstance(item.data, dict):
        return item.model_dump(warnings=False)

    tables = item.data.get("tables")
    if not isinstance(tables, dict):
        return item.model_dump(warnings=False)

    compact_tables: list[dict] = []
    for table_key, table_meta in tables.items():
        if not isinstance(table_meta, dict):
            continue
        compact_tables.append(
            {
                "table": table_key,
                "column_count": table_meta.get("column_count"),
                "columns": table_meta.get("column_names"),
            }
        )

    return {
        "tool": item.tool,
        "args": item.args,
        "data": {"table_count": len(compact_tables), "tables": compact_tables},
    }


def _tool_detail(item: ToolExecution) -> str:
    if isinstance(item.data, dict) and "error" in item.data:
        error = item.data["error"]
        if isinstance(error, dict):
            return error.get("message", "Error")
        return str(error)
    if isinstance(item.data, dict) and "row_count" in item.data:
        return f"Returned {item.data['row_count']} row(s)."
    return "Complete."


def _extract_artifact(
    item: ToolExecution,
    workspace_repo: WorkspaceRepository,
    session_id: str,
) -> dict | None:
    if not isinstance(item.data, dict) or "error" in item.data:
        return None
    if item.tool == "run_python" and "image" in item.data:
        return {"type": "image", "format": item.data.get("format", "png"), "image": item.data["image"]}
    if item.tool == "save_result" and "saved" in item.data:
        name = item.data["saved"]
        rows = workspace_repo.load(session_id, name) or []
        return {"type": "dataset", "name": name, "row_count": item.data.get("row_count", 0), "rows": rows}
    return None


def _artifact_title(artifact: dict) -> str:
    if artifact.get("type") == "image":
        return "Chart generated"
    if artifact.get("type") == "dataset":
        return f"Dataset: {artifact.get('name', 'result')}"
    return "Artifact"


def _content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(part.strip() for part in parts if part and part.strip()).strip()
    return ""
