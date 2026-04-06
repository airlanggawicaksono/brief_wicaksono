import json
import re
from collections.abc import Generator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, ToolMessage

from app.core.llm_utils import chunk_to_text
from app.policy.query import QueryPolicy
from app.policy.tool import ToolPolicy
from app.repository.chat_memory import ChatMessage
from app.services.agent.dto import ToolExecution
from app.services.agent.executor import ToolExecutor
from app.services.agent.message import MessageBuilder
from app.services.tools import build_tool_context


class AgentService:
    """Orchestrates the agentic tool loop: invoke LLM, execute tools, repeat."""

    def __init__(
        self,
        provider: BaseChatModel,
        tool_policy: ToolPolicy,
        tools: list,
        query_policy: QueryPolicy,
    ):
        self.provider = provider
        self.tool_policy = tool_policy
        self._executor = ToolExecutor(tools)
        self._message_builder = MessageBuilder(
            tool_context=build_tool_context(query_policy, tools),
        )

    def execute(
        self,
        text: str,
        history: list[ChatMessage] | None = None,
        intent: str = "data_query",
        entities: dict | None = None,
        language: str = "English",
    ) -> Generator[ToolExecution | str]:
        allowed_names = self.tool_policy.allowed_tools_for_intent(intent)
        allowed_tools = self._executor.filter_tools(allowed_names)
        llm = self.provider.bind_tools(allowed_tools) if allowed_tools else self.provider

        conversation = self._message_builder.build(text, history, entities=entities)
        lang_hint = SystemMessage(content=f"Language rule: respond in {language}.")
        used_lookup_schema = False
        used_data_fetch = False
        forced_concrete_fetch_once = False

        for round_idx in range(self.tool_policy.max_tool_rounds + 1):
            full_response = None
            round_text_parts: list[str] = []
            for chunk in llm.stream([*conversation, lang_hint]):
                full_response = (full_response + chunk) if full_response else chunk
                chunk_text = chunk_to_text(chunk.content)
                if chunk_text:
                    round_text_parts.append(chunk_text)

            if full_response is None:
                return

            round_text = "".join(round_text_parts)
            calls = full_response.tool_calls or []
            if not calls:
                if self._should_force_concrete_data_fetch(
                    intent=intent,
                    user_text=text,
                    used_lookup_schema=used_lookup_schema,
                    used_data_fetch=used_data_fetch,
                    already_forced=forced_concrete_fetch_once,
                ):
                    forced_concrete_fetch_once = True
                    conversation.append(full_response)
                    conversation.append(
                        SystemMessage(
                            content=(
                                "You have only identified structure. "
                                "Now fetch concrete business rows/values and answer directly. "
                                "Do not stop at structure-only explanation."
                            )
                        )
                    )
                    continue
                if round_text:
                    yield round_text
                return

            if round_idx >= self.tool_policy.max_tool_rounds:
                break

            conversation.append(full_response)
            for call in calls:
                tool_name = call["name"]
                tool_args = call["args"]

                if tool_name not in allowed_names:
                    continue
                if not self._executor.is_available(tool_name):
                    continue

                if tool_name == "lookup_schema":
                    used_lookup_schema = True
                if tool_name in {"query_table", "save_result"}:
                    used_data_fetch = True

                yield ToolExecution(tool=tool_name, args=tool_args, data=None)

                output = self._executor.invoke(tool_name, tool_args)
                yield ToolExecution(tool=tool_name, args=tool_args, data=output)

                tool_call_id = call.get("id") or f"{tool_name}_call"
                conversation.append(
                    ToolMessage(
                        tool_call_id=tool_call_id,
                        content=self._serialize(output),
                    )
                )

        yield "I wasn't able to fully resolve your query within the allowed steps. Try rephrasing or narrowing your question."

    def _serialize(self, output: object) -> str:
        if isinstance(output, str):
            return output
        try:
            return json.dumps(output, ensure_ascii=False, default=str)
        except TypeError:
            return str(output)

    @staticmethod
    def _is_technical_structure_request(user_text: str) -> bool:
        lowered = user_text.lower()
        tokens = (
            "schema",
            "table",
            "tables",
            "column",
            "columns",
            "field",
            "fields",
            "sql",
            "query structure",
            "struktur",
            "kolom",
            "tabel",
            "skema",
        )
        if any(token in lowered for token in tokens):
            return True
        return bool(re.search(r"\b(ddl|erd)\b", lowered))

    def _should_force_concrete_data_fetch(
        self,
        *,
        intent: str,
        user_text: str,
        used_lookup_schema: bool,
        used_data_fetch: bool,
        already_forced: bool,
    ) -> bool:
        if intent.strip().lower() != "data_query":
            return False
        if already_forced:
            return False
        if used_data_fetch:
            return False
        if not used_lookup_schema:
            return False
        if self._is_technical_structure_request(user_text):
            return False
        return True
