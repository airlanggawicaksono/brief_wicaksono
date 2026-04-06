import json
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from app.repository.chat_memory import ChatMessage


class MessageBuilder:
    """Builds the LangChain message list for the agent conversation."""

    def __init__(self, tool_context: str):
        self._tool_context = tool_context

    def build(
        self,
        text: str,
        history: list[ChatMessage] | None = None,
        entities: dict | None = None,
    ) -> list[BaseMessage]:
        # Prompt-agnostic context: behavior should come from tools + policy constraints.
        messages: list[BaseMessage] = [
            SystemMessage(content=self._tool_context),
        ]
        if entities:
            messages.append(
                SystemMessage(content=f"Extracted entities from user input: {json.dumps(entities, ensure_ascii=False)}")
            )
        elif history:
            # short follow-up with no new entities — remind the agent this is a
            # continuation so it uses history context rather than starting fresh
            messages.append(
                SystemMessage(
                    content="This is a follow-up to the previous turn. Use conversation history to understand what the user is referring to."
                )
            )
        if history:
            for entry in history:
                if entry["role"] == "user":
                    messages.append(HumanMessage(content=entry["content"]))
                elif entry["role"] == "assistant":
                    messages.append(AIMessage(content=entry["content"]))

        messages.append(HumanMessage(content=text))
        return messages
