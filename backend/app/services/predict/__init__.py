import json
from collections.abc import Generator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import ValidationError

from app.core.intents import Intent
from app.core.infra.cache import get_cached, put_cached
from app.policy.intent import IntentPolicy
from app.prompts.clarification import CLARIFICATION_PROMPT
from app.prompts.general import GENERAL_PROMPT
from app.prompts.summarize import EMPTY_RESPONSE_RETRY
from app.repository.chat_memory import RedisChatMemory
from app.services.agent import AgentService
from app.services.agent.dto import ToolExecution
from app.services.intent import IntentService
from app.services.predict.dto import PredictResult, ProcessStep


class PredictService:
    """Orchestrator: detect intent -> delegate to agent or direct LLM -> stream SSE."""

    def __init__(
        self,
        provider: BaseChatModel,
        intent_service: IntentService,
        agent_service: AgentService,
        intent_policy: IntentPolicy,
        chat_memory: RedisChatMemory,
    ):
        self.provider = provider
        self.intent_service = intent_service
        self.agent_service = agent_service
        self.intent_policy = intent_policy
        self.chat_memory = chat_memory

    def run_stream(self, text: str, session_id: str) -> Generator[str]:
        cached = get_cached(text, scope_key=session_id)
        if cached:
            try:
                cached_result = PredictResult.model_validate(cached)
                yield f"event: cached\ndata: {cached_result.model_dump_json(warnings=False)}\n\n"
                yield "event: done\ndata: {}\n\n"
                return
            except ValidationError:
                pass

        process: list[ProcessStep] = []
        event_buffer: list[str] = []

        def emit_process(stage: str, title: str, detail: str) -> None:
            exists = any(item.stage == stage and item.detail == detail for item in process)
            if exists:
                return
            step = ProcessStep(stage=stage, title=title, detail=detail)
            process.append(step)
            event_buffer.append(f"event: process\ndata: {step.model_dump_json(warnings=False)}\n\n")

        def flush_events() -> Generator[str]:
            while event_buffer:
                yield event_buffer.pop(0)

        emit_process("received_input", "Received input", "Starting intent detection.")
        yield from flush_events()

        extraction = self.intent_service.detect(text)
        yield f"event: extraction\ndata: {extraction.model_dump_json(warnings=False)}\n\n"

        emit_process("intent_detected", "Intent detected", "Intent classification complete.")
        yield from flush_events()

        history = self.chat_memory.load_messages(session_id=session_id, limit=20)
        tool_results: list[ToolExecution] = []
        message = ""
        mode = "direct"

        is_data_intent = self.intent_policy.is_data_intent(extraction.intent)
        if is_data_intent:
            emit_process("agent_started", "Agent started", "Agent is analyzing the request and selecting tools.")
            yield from flush_events()

            for item in self.agent_service.execute(text, history, intent=extraction.intent):
                if isinstance(item, ToolExecution):
                    if item.data is None:
                        if item.tool == "query_table":
                            emit_process(
                                "validate",
                                "Validating query plan",
                                "Validating plan against current schema metadata.",
                            )
                            yield from flush_events()
                        yield f"event: tool_start\ndata: {item.model_dump_json(warnings=False)}\n\n"
                        continue

                    tool_results.append(item)
                    yield f"event: tool_end\ndata: {item.model_dump_json(warnings=False)}\n\n"

                    if item.tool == "lookup_schema":
                        emit_process("lookup_schema", "Schema metadata refreshed", "LLM refreshed schema context.")
                        yield from flush_events()

                    if item.tool == "query_table" and isinstance(item.data, dict):
                        error_payload = item.data.get("error")
                        if error_payload:
                            error_msg = _extract_error_message(error_payload)
                            emit_process("validate", "Plan rejected, replanning", error_msg)
                        else:
                            mode = "query_table"
                            row_count = item.data.get("row_count")
                            emit_process(
                                "execute",
                                "Query executed",
                                f"Returned {row_count if isinstance(row_count, int) else 0} row(s).",
                            )
                        yield from flush_events()
                    continue

                if isinstance(item, str):
                    message = item
                    yield f"event: message\ndata: {json.dumps(message)}\n\n"

            if tool_results:
                emit_process("tools_executed", "Tools executed", ", ".join(t.tool for t in tool_results))
            else:
                emit_process("direct_response", "Direct response", "No data tool execution was needed.")
            emit_process("summarize", "Summarizing result", "Preparing final response for the user.")
            emit_process("response_ready", "Response generated", "Done.")
        else:
            emit_process("direct_response", "Direct response", "No data tool execution was needed.")
            emit_process("summarize", "Summarizing result", "Preparing final response for the user.")
            emit_process("response_ready", "Response generated", "Done.")
            yield from flush_events()

            message = self._build_non_data_message(text, extraction.intent, history)
            yield f"event: message\ndata: {json.dumps(message)}\n\n"

        yield from flush_events()

        result = PredictResult(
            input=text,
            extraction=extraction,
            mode=mode,
            tool_results=tool_results,
            process=process,
            message=message,
        )
        put_cached(text, result.model_dump(warnings=False), scope_key=session_id)
        self.chat_memory.append_turn(
            session_id=session_id,
            user_text=text,
            assistant_text=message,
        )

        yield f"event: result\ndata: {result.model_dump_json(warnings=False)}\n\n"
        yield "event: done\ndata: {}\n\n"

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

    def _build_non_data_message(self, text: str, intent: str, history: list | None = None) -> str:
        system_content = CLARIFICATION_PROMPT if intent == Intent.CLARIFICATION else GENERAL_PROMPT

        messages: list = [
            SystemMessage(content=system_content),
        ]

        if history:
            for entry in history:
                if entry["role"] == "user":
                    messages.append(HumanMessage(content=entry["content"]))
                elif entry["role"] == "assistant":
                    messages.append(AIMessage(content=entry["content"]))

        messages.append(HumanMessage(content=text))
        response = self.provider.invoke(messages)
        content = _content_to_text(response.content)
        if content:
            return content

        retry_messages = [
            *messages,
            SystemMessage(content=EMPTY_RESPONSE_RETRY),
        ]
        retry_response = self.provider.invoke(retry_messages)
        retry_text = _content_to_text(retry_response.content)
        if retry_text:
            return retry_text

        return "Could you clarify what you need about products, audiences, campaigns, or performance?"


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


def _extract_error_message(payload: object) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
        code = payload.get("code")
        if isinstance(code, str) and code.strip():
            return code.strip()
    return "Unknown query error"
