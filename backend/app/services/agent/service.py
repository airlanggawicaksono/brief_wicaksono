import json
from collections.abc import Generator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import ToolMessage

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
    ) -> Generator[ToolExecution | str]:
        allowed_names = self.tool_policy.allowed_tools_for_intent(intent)
        allowed_tools = self._executor.filter_tools(allowed_names)
        llm = self.provider.bind_tools(allowed_tools) if allowed_tools else self.provider

        conversation = self._message_builder.build(text, history, entities=entities)

        for round_idx in range(self.tool_policy.max_tool_rounds + 1):
            full_response = None
            for chunk in llm.stream(conversation):
                full_response = (full_response + chunk) if full_response else chunk
                chunk_text = chunk_to_text(chunk.content)
                if chunk_text:
                    yield chunk_text

            if full_response is None:
                return

            calls = full_response.tool_calls or []
            if not calls:
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
