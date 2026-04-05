from dataclasses import dataclass, field

from app.core.enums.intents import Intent


@dataclass(frozen=True)
class ToolPolicy:
    """Controls tool exposure and multi-step tool orchestration."""

    tool_allowlist_by_intent: dict[str, set[str]] = field(
        default_factory=lambda: {
            Intent.DATA_QUERY: {"lookup_schema", "query_table", "save_result", "list_workspace", "run_python"},
            Intent.GENERAL: set(),
            Intent.CLARIFICATION: set(),
        }
    )
    default_allowlist: set[str] = field(default_factory=set)
    max_tool_rounds: int = 25

    def allowed_tools_for_intent(self, intent: str) -> set[str]:
        return set(self.tool_allowlist_by_intent.get(intent, self.default_allowlist))
