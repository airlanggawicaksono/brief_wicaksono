from pydantic import BaseModel


class PredictRequest(BaseModel):
    text: str


class Entities(BaseModel):
    category: str | None = None
    target: str | None = None
    price_max: int | None = None


class PredictResponse(BaseModel):
    intent: str
    entities: Entities


class ProductResponse(BaseModel):
    id: int
    name: str
    category: str
    target: str
    price: int
    description: str

    model_config = {"from_attributes": True}
