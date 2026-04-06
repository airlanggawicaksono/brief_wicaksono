from typing import Any

from pydantic import BaseModel, Field


class IntentExtraction(BaseModel):
    """Extracted intent and entities from natural language input."""

    intent: str = Field(description="The user's intent: data_query, general, or clarification")
    entities: dict[str, Any] | None = Field(
        default=None,
        description="Freeform key-value entities summarising what the user wants. Only present for data_query.",
    )
    language: str = Field(
        default="English",
        description=(
            "The language to respond in. "
            "Infer from the most recent user message in conversation history that has a clear language signal. "
            "Use the previous user message if the current one is too short or ambiguous. "
            "Examples: 'Indonesian', 'English', 'Japanese'."
        ),
    )
