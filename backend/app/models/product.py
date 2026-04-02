from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100), index=True)
    target: Mapped[str] = mapped_column(String(100), index=True)
    price: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, default="")
