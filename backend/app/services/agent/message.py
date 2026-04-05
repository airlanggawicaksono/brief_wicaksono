from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.prompts.tool_agent import TOOL_AGENT_PROMPT


class MessageBuilder:
    """Builds the LangChain message list for the agent conversation."""

    def __init__(self, tool_context: str):
        self._tool_context = tool_context

    def build(self, text: str, history: list | None = None) -> list[BaseMessage]:
        messages: list[BaseMessage] = [
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

        messages.append(HumanMessage(content=text))
        return messages
