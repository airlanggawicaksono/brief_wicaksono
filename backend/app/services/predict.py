from app.dto.predict import Entities, PredictResponse
from app.models.product import Product
from app.repository.product import ProductRepository


class PredictService:
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo

    def predict(self, text: str) -> PredictResponse:
        """Stub — replace with actual LLM call later."""
        return PredictResponse(
            intent="product_search",
            entities=Entities(),
        )

    def search_products(self, entities: Entities) -> list[Product]:
        return self.product_repo.search(
            category=entities.category,
            target=entities.target,
            price_max=entities.price_max,
        )
