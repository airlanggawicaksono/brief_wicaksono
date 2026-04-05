import json
from collections.abc import Generator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, ToolMessage

from app.policy.tool import ToolPolicy
from app.services.agent.dto import ToolExecution
from app.services.agent.executor import ToolExecutor
from app.services.agent.message import MessageBuilder


class AgentService:
    """Orchestrates the agentic tool loop: invoke LLM, execute tools, repeat."""

    def __init__(
        self,
        provider: BaseChatModel,
        tool_policy: ToolPolicy,
        message_builder: MessageBuilder,
        executor: ToolExecutor,
    ):
        self.provider = provider
        self.tool_policy = tool_policy
        self.message_builder = message_builder
        self.executor = executor

    def execute(
        self,
        text: str,
        history: list | None = None,
        intent: str = "data_query",
    ) -> Generator[ToolExecution | str]:
        allowed_names = self.tool_policy.allowed_tools_for_intent(intent)
        allowed_tools = self.executor.filter_tools(allowed_names)
        llm = self.provider.bind_tools(allowed_tools) if allowed_tools else self.provider

        conversation = self.message_builder.build(text, history)
        response = llm.invoke(conversation)

        for _ in range(self.tool_policy.max_tool_rounds):
            calls = response.tool_calls or []
            if not calls:
                message = self._extract_text(response.content)
                if message:
                    yield message
                return

            conversation.append(response)
            for call in calls:
                tool_name = call["name"]
                tool_args = call["args"]

                if tool_name not in allowed_names:
                    continue
                if not self.executor.is_available(tool_name):
                    continue

                yield ToolExecution(tool=tool_name, args=tool_args, data=None)

                output = self.executor.invoke(tool_name, tool_args)
                yield ToolExecution(tool=tool_name, args=tool_args, data=output)

                tool_call_id = call.get("id") or f"{tool_name}_call"
                conversation.append(
                    ToolMessage(
                        tool_call_id=tool_call_id,
                        content=self._serialize(output),
                    )
                )

                if tool_name == "query_table" and self._is_schema_error(output):
                    conversation.append(
                        SystemMessage(
                            content="Your query failed due to an unknown table or column. "
                            "You MUST call lookup_schema now to discover the correct names. "
                            "Do NOT guess table names."
                        )
                    )

            response = llm.invoke(conversation)

    def _extract_text(self, content: object) -> str:
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
            return " ".join(p.strip() for p in parts if p and p.strip()).strip()
        return ""

    def _serialize(self, output: object) -> str:
        if isinstance(output, str):
            return output
        try:
            return json.dumps(output, ensure_ascii=False, default=str)
        except TypeError:
            return str(output)

    def _is_schema_error(self, output: object) -> bool:
        if not isinstance(output, dict):
            return False
        error = output.get("error", {})
        if not isinstance(error, dict):
            return False
        msg = error.get("message", "").lower()
        return "not allowed" in msg or "not found" in msg
