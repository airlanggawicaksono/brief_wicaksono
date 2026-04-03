from sqlalchemy.orm import Session, Query

from app.models.product import Product
from app.repository.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, db: Session):
        super().__init__(Product, db)

    def search(
        self,
        category: str | None = None,
        brand: str | None = None,
        price_max: int | None = None,
    ) -> list[Product]:
        q: Query = self.db.query(Product)
        if category:
            q = q.filter(Product.category.ilike(f"%{category}%"))
        if brand:
            q = q.filter(Product.brand.ilike(f"%{brand}%"))
        if price_max:
            q = q.filter(Product.price <= price_max)
        return q.all()
