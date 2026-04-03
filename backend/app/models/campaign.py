from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"))
    audience_id: Mapped[int] = mapped_column(Integer, ForeignKey("audiences.id"))
    budget: Mapped[int] = mapped_column(Integer)
