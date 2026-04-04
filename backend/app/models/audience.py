from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config.database import ProductBase


class Audience(ProductBase):
    __tablename__ = "audiences"
    __table_args__ = {"schema": "product"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    min_age: Mapped[int] = mapped_column(Integer, index=True)
    max_age: Mapped[int] = mapped_column(Integer, index=True)
    preferences: Mapped[str] = mapped_column(String(500))

    def __repr__(self) -> str:
        return (
            f"Audience(id={self.id}, name='{self.name}', min_age={self.min_age}, max_age={self.max_age}, "
            f"preferences='{self.preferences}')"
        )
