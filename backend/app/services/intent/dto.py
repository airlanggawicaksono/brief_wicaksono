from typing import Any

from pydantic import BaseModel, Field


class PredictResponse(BaseModel):
    """Extracted intent and entities from natural language input."""

    intent: str = Field(description="The user's intent: data_query, general, or clarification")
    entities: dict[str, Any] | None = Field(
        default=None,
        description="Freeform key-value entities summarising what the user wants. Only present for data_query.",
    )
