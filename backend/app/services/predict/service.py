from collections.abc import Generator

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.enums.event_type import EventType, Stage
from app.policy.intent import IntentPolicy
from app.repository.chat_memory import RedisChatMemory
from app.repository.workspace import WorkspaceRepository
from app.services.agent import AgentService
from app.services.intent import IntentService
from app.services.predict.dto import (
    ProcessEvent,
    PredictResult,
    RequestContext,
    ResponseOutput,
)
from app.services.predict.presenter import SsePresenter
from app.services.predict.strategy import (
    AgentResponseStrategy,
    DirectResponseStrategy,
    ResponseStrategy,
)


class PredictService:
    """Orchestrator: detects intent, dispatches to the right strategy, streams SSE."""

    def __init__(
        self,
        intent_service: IntentService,
        intent_policy: IntentPolicy,
        agent_service: AgentService,
        provider: BaseChatModel,
        chat_memory: RedisChatMemory,
        workspace_repo: WorkspaceRepository,
    ):
        self._intent_service = intent_service
        self._intent_policy = intent_policy
        self._strategies: dict[str, ResponseStrategy] = {
            "agent": AgentResponseStrategy(agent_service, workspace_repo),
            "direct": DirectResponseStrategy(provider),
        }
        self._chat_memory = chat_memory
        self._presenter = SsePresenter()

    def run_stream(self, text: str, session_id: str) -> Generator[str]:
        history = self._chat_memory.load_messages(session_id=session_id, limit=20)
        ctx = RequestContext(session_id=session_id, text=text, history=history)

        all_events: list[ProcessEvent] = []

        # ── intent detection ────────────────────────────────
        extraction, ok = self._detect_intent(ctx, all_events)
        yield from (self._presenter.render(e) for e in all_events)
        if not ok:
            yield self._presenter.done()
            return

        # ── strategy dispatch (single unified loop) ─────────
        strategy = self._resolve_strategy(extraction.intent)
        output: ResponseOutput | None = None
        for item in strategy.execute(extraction, ctx):
            if isinstance(item, ProcessEvent):
                all_events.append(item)
                yield self._presenter.render(item)
            elif isinstance(item, ResponseOutput):
                output = item

        result = PredictResult(
            input=text,
            extraction=extraction,
            mode=output.mode,
            tool_results=output.tool_results,
            process=all_events,
            message=output.message,
            artifacts=output.artifacts,
        )
        self._save_turn(ctx, output.message)
        yield self._presenter.result(result)
        yield self._presenter.done()

    def reset_session(self, session_id: str) -> None:
        self._chat_memory.clear(session_id)

    def list_session_history(self, session_id: str, limit: int = 20) -> list[dict]:
        messages = self._chat_memory.load_messages(session_id=session_id, limit=max(1, limit))
        turns: list[dict] = []

        idx = 0
        while idx < len(messages):
            current = messages[idx]
            if current.get("role") != "user":
                idx += 1
                continue

            user_text = current.get("content", "")
            assistant_text = ""
            if idx + 1 < len(messages) and messages[idx + 1].get("role") == "assistant":
                assistant_text = messages[idx + 1].get("content", "")
                idx += 2
            else:
                idx += 1

            turns.append({"input": user_text, "message": assistant_text})
        return turns

    # ── private ─────────────────────────────────────────────

    def _detect_intent(self, ctx: RequestContext, events: list[ProcessEvent]) -> tuple:
        """Run intent detection, append events. Returns (extraction, ok)."""
        events.append(
            ProcessEvent(
                type=EventType.PROCESS,
                stage=Stage.RECEIVED_INPUT,
                title="Received input",
                detail="Starting intent detection.",
            )
        )
        try:
            extraction = self._intent_service.detect(ctx.text, history=ctx.history)
        except Exception as exc:
            events.append(
                ProcessEvent(
                    type=EventType.ERROR,
                    stage=Stage.FAILED,
                    title="Intent detection failed",
                    detail=str(exc),
                )
            )
            return None, False

        events.append(
            ProcessEvent(
                type=EventType.EXTRACTION,
                stage=Stage.INTENT_DETECTED,
                title="Intent detected",
                detail=extraction.intent,
                data=extraction.model_dump(warnings=False),
            )
        )
        return extraction, True

    def _resolve_strategy(self, intent: str) -> ResponseStrategy:
        if self._intent_policy.is_data_intent(intent):
            return self._strategies["agent"]
        return self._strategies["direct"]

    def _save_turn(self, ctx: RequestContext, message: str) -> None:
        self._chat_memory.append_turn(
            session_id=ctx.session_id,
            user_text=ctx.text,
            assistant_text=message,
        )
