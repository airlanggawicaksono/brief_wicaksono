from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config.database import MarketingBase


class Campaign(MarketingBase):
    __tablename__ = "campaigns"
    __table_args__ = {"schema": "marketing"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("product.products.id"))
    audience_id: Mapped[int] = mapped_column(Integer, ForeignKey("product.audiences.id"))
    budget: Mapped[int] = mapped_column(Integer)

    def __repr__(self) -> str:
        return (
            f"Campaign(id={self.id}, name='{self.name}', product_id={self.product_id}, "
            f"audience_id={self.audience_id}, budget={self.budget})"
        )
