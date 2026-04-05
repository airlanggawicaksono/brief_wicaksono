import json
from collections.abc import Generator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import ValidationError

from app.policy.tool import ToolPolicy
from app.prompts.summarize import SUMMARIZE_PROMPT
from app.prompts.tool_agent import TOOL_AGENT_PROMPT
from app.services.agent.dto import ToolExecution


class AgentService:
    """Agentic tool loop: binds tools to LLM, executes calls, yields results."""

    def __init__(
        self,
        provider: BaseChatModel,
        tools: list,
        tool_policy: ToolPolicy,
        tool_context: str,
    ):
        self.provider = provider
        self.tool_policy = tool_policy
        self._tools = tools
        self._tool_map = {tool.name: tool for tool in self._tools}
        self._tool_context = tool_context

    def execute(
        self,
        text: str,
        history: list | None = None,
        intent: str = "data_query",
    ) -> Generator[ToolExecution | str]:
        allowed_tool_names = self.tool_policy.allowed_tools_for_intent(intent)
        allowed_tools = [t for t in self._tools if t.name in allowed_tool_names]
        llm_with_tools = self.provider.bind_tools(allowed_tools) if allowed_tools else self.provider

        messages: list = [
            SystemMessage(content=TOOL_AGENT_PROMPT),
            SystemMessage(content=self._tool_context),
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

        for _ in range(self.tool_policy.max_tool_rounds):
            calls = response.tool_calls or []
            if not calls:
                message_text = self._content_to_text(response.content)
                if message_text:
                    yield message_text
                    return

                synthesized = self._summarize_tool_results(text, executed_tools)
                if synthesized:
                    yield synthesized
                    return

                yield self._fallback_from_tool_results(executed_tools)
                return

            conversation.append(response)
            for call in calls:
                tool_name = call["name"]
                tool_args = call["args"]

                if tool_name not in allowed_tool_names:
                    continue

                tool_fn = self._tool_map.get(tool_name)
                if not tool_fn:
                    continue

                yield ToolExecution(tool=tool_name, args=tool_args, data=None)
                try:
                    output = tool_fn.invoke(tool_args)
                except ValidationError as exc:
                    output = {
                        "error": {
                            "code": "tool_validation_error",
                            "message": str(exc),
                            "details": exc.errors(),
                            "input": tool_args,
                        }
                    }
                except Exception as exc:
                    output = {"error": {"code": "tool_runtime_error", "message": str(exc) or "Tool failed"}}

                ui_output = self._tool_output_for_ui(tool_name, output)
                tool_execution = ToolExecution(tool=tool_name, args=tool_args, data=ui_output)
                executed_tools.append(tool_execution)
                yield tool_execution

                tool_call_id = call.get("id") or f"{tool_name}_call"
                conversation.append(
                    ToolMessage(
                        tool_call_id=tool_call_id,
                        content=self._serialize_tool_output(output),
                    )
                )

            response = llm_with_tools.invoke(conversation)

        yield self._fallback_from_tool_results(executed_tools)

    def _summarize_tool_results(self, user_text: str, tool_results: list[ToolExecution]) -> str:
        if not tool_results:
            return ""

        payload = [{"tool": t.tool, "args": t.args, "data": t.data} for t in tool_results]

        try:
            payload_json = json.dumps(payload, ensure_ascii=False)
        except TypeError:
            payload_json = str(payload)
        if len(payload_json) > 6000:
            payload_json = payload_json[:6000] + "...(truncated)"

        messages = [
            SystemMessage(content=SUMMARIZE_PROMPT),
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
            "table_count": len(compact_tables),
            "tables": compact_tables,
        }

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

    def _serialize_tool_output(self, output: object) -> str:
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
