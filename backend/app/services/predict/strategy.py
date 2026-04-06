from __future__ import annotations

from collections.abc import Generator
from typing import Protocol, runtime_checkable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.enums.event_type import EventType, Stage
from app.core.enums.intents import Intent
from app.core.llm_utils import content_to_text
from app.prompts.clarification import CLARIFICATION_PROMPT
from app.prompts.general import GENERAL_PROMPT
from app.repository.workspace import WorkspaceRepository
from app.services.agent import AgentService
from app.services.agent.dto import ToolExecution
from app.services.intent.dto import IntentExtraction
from app.services.predict.dto import (
    Artifact,
    ProcessEvent,
    RequestContext,
    ResponseOutput,
)
from app.services.predict.presenter import ToolResultFormatter


@runtime_checkable
class ResponseStrategy(Protocol):
    """Uniform contract: yield ProcessEvents during execution, yield ResponseOutput at the end."""

    def execute(
        self, extraction: IntentExtraction, ctx: RequestContext
    ) -> Generator[ProcessEvent | ResponseOutput]: ...


class AgentResponseStrategy:
    """Data-query path: runs the agent tool loop, streams events, extracts artifacts."""

    def __init__(self, agent_service: AgentService, workspace_repo: WorkspaceRepository):
        self._agent_service = agent_service
        self._workspace_repo = workspace_repo

    def execute(
        self, extraction: IntentExtraction, ctx: RequestContext
    ) -> Generator[ProcessEvent | ResponseOutput]:
        yield ProcessEvent(
            type=EventType.PROCESS,
            stage=Stage.AGENT_STARTED,
            title="Agent started",
            detail="Selecting tools.",
        )

        tool_results: list[ToolExecution] = []
        artifacts: list[Artifact] = []
        message = ""

        entities = extraction.entities if isinstance(extraction.entities, dict) else None
        for item in self._agent_service.execute(
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
                    is_error = ToolResultFormatter.is_error(item)
                    if not is_error:
                        tool_results.append(item)
                    yield ProcessEvent(
                        type=EventType.TOOL_END,
                        stage=Stage.TOOL_FINISHED,
                        title=f"{item.tool} finished",
                        detail=ToolResultFormatter.detail(item),
                        data=ToolResultFormatter.compact_for_ui(item, is_error=is_error),
                    )
                    artifact = self._try_extract_artifact(item, ctx.session_id)
                    if artifact:
                        artifacts.append(artifact)
                        yield ProcessEvent(
                            type=EventType.ARTIFACT,
                            stage=Stage.ARTIFACT_READY,
                            title=self._artifact_title(artifact),
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

        yield ResponseOutput(
            tool_results=tool_results,
            message=message,
            artifacts=artifacts,
            mode="agent" if tool_results else "direct",
        )

    def _try_extract_artifact(self, item: ToolExecution, session_id: str) -> Artifact | None:
        if not isinstance(item.data, dict) or "error" in item.data:
            return None
        if item.tool == "run_python" and "image" in item.data:
            return Artifact(
                type="image",
                format=item.data.get("format", "png"),
                image=item.data["image"],
            )
        if item.tool == "save_result" and "saved" in item.data:
            name = item.data["saved"]
            rows = self._workspace_repo.load(session_id, name) or []
            return Artifact(
                type="dataset",
                name=name,
                row_count=item.data.get("row_count", 0),
                rows=rows,
            )
        return None

    @staticmethod
    def _artifact_title(artifact: Artifact) -> str:
        if artifact.type == "image":
            return "Chart generated"
        if artifact.type == "dataset":
            return f"Dataset: {artifact.name or 'result'}"
        return "Artifact"


class DirectResponseStrategy:
    """Non-data path (general, clarification): plain LLM call, no tools."""

    def __init__(self, provider: BaseChatModel):
        self._provider = provider

    def execute(
        self, extraction: IntentExtraction, ctx: RequestContext
    ) -> Generator[ProcessEvent | ResponseOutput]:
        yield ProcessEvent(
            type=EventType.PROCESS,
            stage=Stage.DIRECT_RESPONSE,
            title="Direct response",
            detail="No tool execution needed.",
        )

        message = self._respond(ctx.text, extraction.intent, ctx.history)

        yield ProcessEvent(
            type=EventType.MESSAGE,
            stage=Stage.RESPONSE_READY,
            title="Response",
            detail=message,
        )

        yield ResponseOutput(message=message, mode="direct")

    def _respond(self, text: str, intent: str, history: list) -> str:
        system_content = CLARIFICATION_PROMPT if intent == Intent.CLARIFICATION else GENERAL_PROMPT
        messages: list = [SystemMessage(content=system_content)]

        for entry in history or []:
            if entry["role"] == "user":
                messages.append(HumanMessage(content=entry["content"]))
            elif entry["role"] == "assistant":
                messages.append(AIMessage(content=entry["content"]))

        messages.append(HumanMessage(content=text))
        response = self._provider.invoke(messages)
        return content_to_text(response.content) or "Could you clarify what you need about products, audiences, campaigns, or performance?"
