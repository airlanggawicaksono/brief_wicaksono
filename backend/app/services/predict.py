import json
from collections.abc import Generator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import ValidationError

from app.core.business_policy.intent_policy import IntentPolicy
from app.core.business_policy.tool_policy import ToolPolicy
from app.core.prompts.tool_agent import TOOL_AGENT_PROMPT
from app.core.technical_policy.cache import get_cached, put_cached
from app.core.technical_policy.retry import retry
from app.dto.predict_result import PredictResult, ProcessStep, ToolExecution
from app.dto.response import PredictResponse
from app.repository.chat_memory import RedisChatMemory
from app.services.extraction import ExtractionService
from app.services.query_tools import QueryToolFactory
from app.services.schema import SchemaService


class PredictService:
    """Main predict orchestration: extract -> metadata -> plan/validate/execute -> summarize."""

    def __init__(
        self,
        provider: BaseChatModel,
        extraction_service: ExtractionService,
        schema_service: SchemaService,
        tool_factory: QueryToolFactory,
        intent_policy: IntentPolicy,
        tool_policy: ToolPolicy,
        chat_memory: RedisChatMemory,
    ):
        self.provider = provider
        self.extraction_service = extraction_service
        self.schema_service = schema_service
        self.intent_policy = intent_policy
        self.tool_policy = tool_policy
        self.chat_memory = chat_memory

        self._tools = tool_factory.get_tools()
        self._tool_map = {tool.name: tool for tool in self._tools}

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

        extraction = self.extraction_service.extract(text)
        extraction = PredictResponse.model_validate(extraction)
        yield f"event: extraction\ndata: {extraction.model_dump_json(warnings=False)}\n\n"

        emit_process("intent_detected", "Intent detected", "Intent classification complete.")
        yield from flush_events()

        history = self.chat_memory.load_messages(session_id=session_id, limit=20)
        tool_results: list[ToolExecution] = []
        message = ""
        mode = "direct"
        metadata_snapshot_hash: str | None = None
        metadata_snapshot_version: str | None = None

        schema_context: dict | None = None
        if self.intent_policy.is_data_intent(extraction.intent):
            schema_context = self.schema_service.get_schema(detail_level="summary")
            if isinstance(schema_context, dict):
                metadata_snapshot_hash = schema_context.get("snapshot_hash")
                metadata_snapshot_version = schema_context.get("snapshot_version")
            emit_process("lookup_schema", "Schema metadata loaded", f"snapshot={metadata_snapshot_version or 'unknown'}")
            emit_process("plan", "Planning query", "Model is preparing a metadata-aware query plan.")
            yield from flush_events()

        for item in self.execute_stream(text, extraction, history=history, schema_context=schema_context):
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

                if item.tool == "lookup_schema" and isinstance(item.data, dict):
                    metadata_snapshot_hash = item.data.get("snapshot_hash", metadata_snapshot_hash)
                    metadata_snapshot_version = item.data.get("snapshot_version", metadata_snapshot_version)
                    emit_process(
                        "lookup_schema",
                        "Schema metadata refreshed",
                        f"snapshot={metadata_snapshot_version or 'unknown'}",
                    )
                    yield from flush_events()

                if item.tool == "query_table" and isinstance(item.data, dict):
                    error_payload = item.data.get("error")
                    if error_payload:
                        error_msg = self._extract_error_message(error_payload)
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
            emit_process("tools_executed", "Tools executed", ", ".join(tool.tool for tool in tool_results))
        else:
            emit_process("direct_response", "Direct response", "No data tool execution was needed.")
        emit_process("summarize", "Summarizing result", "Preparing final response for the user.")
        emit_process("response_ready", "Response generated", "Done.")
        yield from flush_events()

        result = PredictResult(
            pipeline_version=4,
            input=text,
            extraction=extraction,
            mode=mode,
            tool_results=tool_results,
            process=process,
            message=message,
            metadata_snapshot_hash=metadata_snapshot_hash,
            metadata_snapshot_version=metadata_snapshot_version,
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

    @retry()
    def execute_stream(
        self,
        text: str,
        extraction: PredictResponse,
        history: list | None = None,
        schema_context: dict | None = None,
    ) -> Generator[ToolExecution | str]:
        if not self.intent_policy.is_data_intent(extraction.intent):
            passthrough = self._build_non_data_message(text, extraction.intent, history)
            yield from self._yield_progressive_text(passthrough)
            return

        if schema_context is None:
            schema_context = self.schema_service.get_schema(detail_level="summary")
        yield from self._execute_with_tools(text, schema_context, history, intent=extraction.intent)

    def _execute_with_tools(
        self,
        text: str,
        schema_context: dict,
        history: list | None = None,
        intent: str = "data_query",
    ) -> Generator[ToolExecution | str]:
        allowed_tool_names = self.tool_policy.allowed_tools_for_intent(intent)
        allowed_tools = [tool for tool in self._tools if tool.name in allowed_tool_names]
        llm_with_tools = self.provider.bind_tools(allowed_tools) if allowed_tools else self.provider

        messages: list = [
            SystemMessage(content=TOOL_AGENT_PROMPT),
            SystemMessage(content=f"Schema context: {json.dumps(schema_context, ensure_ascii=False)}"),
            SystemMessage(content=f"Allowed tools: {sorted(allowed_tool_names)}"),
            SystemMessage(content=f"User language hint: reply in the same language as this input -> {text}"),
        ]

        if history:
            for entry in history:
                if entry["role"] == "user":
                    messages.append(HumanMessage(content=entry["content"]))
                elif entry["role"] == "assistant":
                    messages.append(AIMessage(content=entry["content"]))

        conversation: list = [*messages, HumanMessage(content=text)]
        response = llm_with_tools.invoke(conversation)
        executed_tools: list[ToolExecution] = []

        latest_schema_context = schema_context
        metadata_loaded = False

        for _ in range(self.tool_policy.max_tool_rounds):
            calls = response.tool_calls or []
            if not calls:
                message_text = self._content_to_text(response.content)
                if message_text:
                    yield from self._yield_progressive_text(message_text)
                    return

                synthesized = self._summarize_tool_results_with_llm(text, executed_tools)
                if synthesized:
                    yield from self._yield_progressive_text(synthesized)
                    return

                yield from self._yield_progressive_text(self._fallback_from_tool_results(executed_tools))
                return

            conversation.append(response)
            for call in calls:
                tool_name = call["name"]
                tool_args = call["args"]

                if tool_name not in allowed_tool_names:
                    continue

                if tool_name == "query_table" and not metadata_loaded:
                    blocked = {
                        "error": {
                            "code": "metadata_required",
                            "message": "metadata-first required: call lookup_schema before query_table",
                        },
                        "hint": "Call lookup_schema and pass snapshot_hash into QueryPlanV2.metadata_hash.",
                    }
                    blocked_exec = ToolExecution(tool=tool_name, args=tool_args, data=blocked)
                    executed_tools.append(blocked_exec)
                    yield blocked_exec

                    tool_call_id = call.get("id") or f"{tool_name}_call"
                    conversation.append(
                        ToolMessage(
                            tool_call_id=tool_call_id,
                            content=self._tool_message_content(blocked),
                        )
                    )
                    continue

                tool_fn = self._tool_map.get(tool_name)
                if not tool_fn:
                    continue

                yield ToolExecution(tool=tool_name, args=tool_args, data=None)
                try:
                    output = tool_fn.invoke(tool_args)
                except Exception as exc:
                    output = {"error": {"code": "tool_runtime_error", "message": str(exc) or "Tool failed"}}

                if tool_name == "lookup_schema" and isinstance(output, dict):
                    latest_schema_context = output
                    metadata_loaded = True
                elif tool_name == "query_table" and isinstance(output, dict):
                    err = output.get("error")
                    if isinstance(err, dict) and err.get("code") == "stale_metadata_hash":
                        metadata_loaded = False

                ui_output = self._tool_output_for_ui(tool_name, output)
                tool_execution = ToolExecution(tool=tool_name, args=tool_args, data=ui_output)
                executed_tools.append(tool_execution)
                yield tool_execution

                tool_call_id = call.get("id") or f"{tool_name}_call"
                conversation.append(
                    ToolMessage(
                        tool_call_id=tool_call_id,
                        content=self._tool_message_content(output),
                    )
                )

            if isinstance(latest_schema_context, dict):
                conversation.append(
                    SystemMessage(
                        content=(
                            "Latest schema snapshot context: "
                            f"{json.dumps(latest_schema_context, ensure_ascii=False)}"
                        )
                    )
                )
            response = llm_with_tools.invoke(conversation)

        yield from self._yield_progressive_text(self._fallback_from_tool_results(executed_tools))

    def _build_non_data_message(self, text: str, intent: str, history: list | None = None) -> str:
        messages: list = [
            SystemMessage(
                content=(
                    "You are a helpful assistant in a marketing analytics app. "
                    "If the user asks greeting/smalltalk, reply naturally and briefly. "
                    "If intent is unclear, ask one clarifying question and provide 2 short examples "
                    "about products, audiences, campaigns, or performance. "
                    "Always respond in the same language as the user's latest message."
                )
            ),
            SystemMessage(content=f"Detected intent: {intent}"),
        ]

        if history:
            for entry in history:
                if entry["role"] == "user":
                    messages.append(HumanMessage(content=entry["content"]))
                elif entry["role"] == "assistant":
                    messages.append(AIMessage(content=entry["content"]))

        messages.append(HumanMessage(content=text))
        response = self.provider.invoke(messages)
        content = self._content_to_text(response.content)
        if content:
            return content

        retry_messages = [
            *messages,
            SystemMessage(content="Your previous response was empty. Reply in one short helpful sentence."),
        ]
        retry_response = self.provider.invoke(retry_messages)
        retry_text = self._content_to_text(retry_response.content)
        if retry_text:
            return retry_text

        return "Could you clarify what you need about products, audiences, campaigns, or performance?"

    def _tool_output_for_ui(self, tool_name: str, output: object) -> object:
        if tool_name != "lookup_schema" or not isinstance(output, dict):
            return output

        tables = output.get("tables")
        if not isinstance(tables, dict):
            return output

        compact_tables: list[dict[str, object]] = []
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
            "snapshot_hash": output.get("snapshot_hash"),
            "snapshot_version": output.get("snapshot_version"),
            "table_count": len(compact_tables),
            "tables": compact_tables,
            "query_tools": output.get("query_tools"),
            "write_operations": (
                output.get("constraints", {}).get("write_operations")
                if isinstance(output.get("constraints"), dict)
                else None
            ),
        }

    def _summarize_tool_results_with_llm(self, user_text: str, tool_results: list[ToolExecution]) -> str:
        if not tool_results:
            return ""

        payload = []
        for item in tool_results:
            payload.append({"tool": item.tool, "args": item.args, "data": item.data})

        try:
            payload_json = json.dumps(payload, ensure_ascii=False)
        except TypeError:
            payload_json = str(payload)
        if len(payload_json) > 6000:
            payload_json = payload_json[:6000] + "...(truncated)"

        messages = [
            SystemMessage(
                content=(
                    "You are a helpful assistant in a marketing analytics app. "
                    "Answer only from tool outputs. If data is empty, say so clearly. "
                    "Reply in the same language as the user's latest message."
                )
            ),
            HumanMessage(content=f"User request: {user_text}"),
            SystemMessage(content=f"Tool outputs: {payload_json}"),
        ]
        try:
            response = self.provider.invoke(messages)
        except Exception:
            return ""
        return self._content_to_text(response.content)

    def _fallback_from_tool_results(self, tool_results: list[ToolExecution]) -> str:
        if not tool_results:
            return "I could not produce a grounded answer from available tools."

        for item in reversed(tool_results):
            if isinstance(item.data, dict) and "error" in item.data:
                return f"I could not complete the query: {self._extract_error_message(item.data.get('error'))}"

        tools = ", ".join(dict.fromkeys(item.tool for item in tool_results))
        row_count = 0
        for item in tool_results:
            if isinstance(item.data, list):
                row_count += len(item.data)
            elif isinstance(item.data, dict):
                rows = item.data.get("rows")
                if isinstance(rows, list):
                    row_count += len(rows)
        if row_count > 0:
            return f"Done. I ran {tools} and found {row_count} row(s)."
        return f"Done. I ran {tools}."

    def _content_to_text(self, content: object) -> str:
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

    def _tool_message_content(self, output: object) -> str:
        if isinstance(output, str):
            return output
        try:
            return json.dumps(output, ensure_ascii=False)
        except TypeError:
            return str(output)

    def _extract_error_message(self, payload: object) -> str:
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

    def _yield_progressive_text(self, text: str, chunk_size: int = 24) -> Generator[str]:
        normalized = text.strip()
        if not normalized:
            return
        if len(normalized) <= chunk_size:
            yield normalized
            return
        built = ""
        for idx in range(0, len(normalized), chunk_size):
            built += normalized[idx: idx + chunk_size]
            yield built
