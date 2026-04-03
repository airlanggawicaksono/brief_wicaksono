from langchain_core.messages import SystemMessage, HumanMessage

from app.core.technical_policy.retry import retry
from app.dependencies.providers.llm import LLMProvider
from app.dependencies.prompts.tool_agent import TOOL_AGENT_PROMPT


class PredictService:
    """Reusable: execute tools via LLM tool calling."""

    def __init__(self, provider: LLMProvider, tools: list):
        self.llm_with_tools = provider.bind_tools(tools)
        self._tool_map = {t.name: t for t in tools}

    @retry()
    def execute(self, text: str) -> dict:
        messages = [
            SystemMessage(content=TOOL_AGENT_PROMPT),
            HumanMessage(content=text),
        ]
        response = self.llm_with_tools.invoke(messages)

        if response.tool_calls:
            tool_results = []
            for call in response.tool_calls:
                tool_fn = self._tool_map.get(call["name"])
                if tool_fn:
                    output = tool_fn.invoke(call["args"])
                    tool_results.append({
                        "tool": call["name"],
                        "args": call["args"],
                        "data": output,
                    })
            return {"tool_results": tool_results, "message": response.content or ""}

        return {"tool_results": [], "message": response.content or ""}
