from dataclasses import dataclass, field

from app.core.enum.intents import Intent


@dataclass(frozen=True)
class IntentPolicy:
    """Business rules for intent classification and routing."""

    data_intents: set[str] = field(default_factory=lambda: {Intent.DATA_QUERY})

    conversational_intents: set[str] = field(
        default_factory=lambda: {Intent.GENERAL, Intent.CLARIFICATION}
    )

    @property
    def all_intents(self) -> set[str]:
        return self.data_intents | self.conversational_intents

    def is_data_intent(self, intent: str) -> bool:
        return intent in self.data_intents

    def normalize(self, intent: str) -> str:
        cleaned = intent.strip().lower().replace(" ", "_")
        if cleaned in self.all_intents:
            return cleaned
        return Intent.CLARIFICATION
