from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100), index=True)
    price: Mapped[int] = mapped_column(Integer)
    brand: Mapped[str] = mapped_column(String(100), index=True)
