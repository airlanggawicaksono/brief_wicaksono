from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import ProductBase


class Product(ProductBase):
    __tablename__ = "products"
    __table_args__ = {"schema": "product"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100), index=True)
    price: Mapped[int] = mapped_column(Integer)
    brand: Mapped[str] = mapped_column(String(100), index=True)

    def __repr__(self) -> str:
        return (
            f"Product(id={self.id}, name='{self.name}', category='{self.category}', "
            f"price={self.price}, brand='{self.brand}')"
        )
