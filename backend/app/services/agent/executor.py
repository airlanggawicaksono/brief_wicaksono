from pydantic import ValidationError


class ToolExecutor:
    """Invokes LangChain tools and normalizes errors."""

    def __init__(self, tools: list):
        self._tool_map: dict = {t.name: t for t in tools}

    def invoke(self, tool_name: str, tool_args: dict) -> object:
        tool_fn = self._tool_map.get(tool_name)
        if not tool_fn:
            return {"error": {"code": "tool_not_found", "message": f"Tool '{tool_name}' not found"}}

        try:
            return tool_fn.invoke(tool_args)
        except ValidationError as exc:
            return {
                "error": {
                    "code": "tool_validation_error",
                    "message": str(exc),
                    "details": exc.errors(),
                    "input": tool_args,
                }
            }
        except Exception as exc:
            return {"error": {"code": "tool_runtime_error", "message": str(exc) or "Tool failed"}}

    def is_available(self, tool_name: str) -> bool:
        return tool_name in self._tool_map

    def filter_tools(self, allowed_names: set[str]) -> list:
        return [t for name, t in self._tool_map.items() if name in allowed_names]
