from pydantic import BaseModel, Field


class Entities(BaseModel):
    category: str | None = Field(None, description="Product category e.g. skincare, makeup, haircare")
    target: str | None = Field(None, description="Audience segment e.g. gen z, millennials, students")
    price_max: int | None = Field(None, description="Maximum price in IDR")


class PredictResponse(BaseModel):
    """Extracted intent and entities from natural language input."""
    intent: str = Field(description="The user's intent")
    entities: Entities = Field(default_factory=Entities, description="Extracted entities")
