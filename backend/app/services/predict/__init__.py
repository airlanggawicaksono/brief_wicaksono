from collections.abc import Generator

from pydantic import ValidationError

from app.core.infra.cache import get_cached, put_cached
from app.repository.chat_memory import RedisChatMemory
from app.services.predict.dto import (
    ProcessEvent,
    PredictResult,
    RequestContext,
)
from app.services.predict.presenter import SsePresenter
from app.services.predict.steps import AgentStep, DirectResponseStep, IntentStep


class PredictService:
    """Orchestrator: chains steps, forwards events through presenter."""

    def __init__(
        self,
        intent_step: IntentStep,
        agent_step: AgentStep,
        direct_step: DirectResponseStep,
        chat_memory: RedisChatMemory,
        presenter: SsePresenter,
    ):
        self.intent_step = intent_step
        self.agent_step = agent_step
        self.direct_step = direct_step
        self.chat_memory = chat_memory
        self.presenter = presenter

    def run_stream(self, text: str, session_id: str) -> Generator[str]:
        history = self.chat_memory.load_messages(session_id=session_id, limit=20)
        ctx = RequestContext(session_id=session_id, text=text, history=history)

        cached = self._try_cache(ctx)
        if cached:
            yield self.presenter.cached(cached)
            yield self.presenter.done()
            return

        all_events: list[ProcessEvent] = []

        intent_result = self.intent_step.run(ctx)
        yield from self._emit(intent_result.events, all_events)
        if not intent_result.ok:
            yield self.presenter.done()
            return
        extraction = intent_result.output

        if self.intent_step.intent_policy.is_data_intent(extraction.intent):
            tool_results = []
            message = ""
            for item in self.agent_step.stream(extraction, ctx):
                if isinstance(item, ProcessEvent):
                    all_events.append(item)
                    yield self.presenter.render(item)
                elif isinstance(item, dict):
                    tool_results = item.get("tool_results", [])
                    message = item.get("message", "")
            mode = "query_table" if tool_results else "direct"
        else:
            direct_result = self.direct_step.run(extraction, ctx)
            yield from self._emit(direct_result.events, all_events)
            tool_results = []
            message = direct_result.output or ""
            mode = "direct"

        result = PredictResult(
            input=text,
            extraction=extraction,
            mode=mode,
            tool_results=tool_results,
            process=all_events,
            message=message,
        )
        self._cache_and_save(ctx, result, message)
        yield self.presenter.result(result)
        yield self.presenter.done()

    def list_session_history(self, session_id: str, limit: int = 20) -> list[dict]:
        messages = self.chat_memory.load_messages(session_id=session_id, limit=max(1, limit))
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

    def _emit(self, events: list[ProcessEvent], collector: list) -> Generator[str]:
        for event in events:
            collector.append(event)
            yield self.presenter.render(event)

    def _try_cache(self, ctx: RequestContext) -> PredictResult | None:
        cached = get_cached(ctx.text, scope_key=ctx.session_id)
        if cached:
            try:
                return PredictResult.model_validate(cached)
            except ValidationError:
                return None
        return None

    def _cache_and_save(self, ctx: RequestContext, result: PredictResult, message: str) -> None:
        put_cached(ctx.text, result.model_dump(warnings=False), scope_key=ctx.session_id)
        self.chat_memory.append_turn(
            session_id=ctx.session_id,
            user_text=ctx.text,
            assistant_text=message,
        )
