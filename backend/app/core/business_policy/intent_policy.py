from dataclasses import dataclass, field


@dataclass(frozen=True)
class IntentPolicy:
    """Business rules for intent classification and routing."""

    data_intents: set[str] = field(default_factory=lambda: {"data_query"})

    passthrough_intents: set[str] = field(default_factory=lambda: {"greeting", "unknown"})

    fallback_intent: str = "unknown"

    @property
    def all_intents(self) -> set[str]:
        return self.data_intents | self.passthrough_intents

    def is_data_intent(self, intent: str) -> bool:
        return intent in self.data_intents

    def is_passthrough(self, intent: str) -> bool:
        return intent in self.passthrough_intents

    def normalize(self, intent: str) -> str:
        cleaned = intent.strip().lower().replace(" ", "_")
        if cleaned in self.all_intents:
            return cleaned
        return self.fallback_intent
