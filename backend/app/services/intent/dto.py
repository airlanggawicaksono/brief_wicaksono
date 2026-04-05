from pydantic import BaseModel, Field


class DataQueryEntities(BaseModel):
    category: str | None = Field(None, description="Product category e.g. skincare, makeup, haircare")
    target: str | None = Field(None, description="Audience segment e.g. gen z, millennials, students")
    price_max: int | None = Field(None, description="Maximum price in IDR")


class PredictResponse(BaseModel):
    """Extracted intent and entities from natural language input."""

    intent: str = Field(description="The user's intent: data_query, general, or clarification")
    entities: DataQueryEntities | None = Field(
        default=None, description="Extracted entities, only present for data_query intent"
    )
