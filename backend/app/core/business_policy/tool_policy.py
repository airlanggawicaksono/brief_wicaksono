from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolPolicy:
    """Controls tool exposure and multi-step tool orchestration."""

    tool_allowlist_by_intent: dict[str, set[str]] = field(
        default_factory=lambda: {
            "data_query": {"lookup_schema", "query_table"},
            "greeting": set(),
            "unknown": set(),
        }
    )
    default_allowlist: set[str] = field(default_factory=set)
    max_tool_rounds: int = 6

    def allowed_tools_for_intent(self, intent: str) -> set[str]:
        return set(self.tool_allowlist_by_intent.get(intent, self.default_allowlist))
