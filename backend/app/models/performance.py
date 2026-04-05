from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import MarketingBase


class Performance(MarketingBase):
    __tablename__ = "performance"
    __table_args__ = {"schema": "marketing"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("marketing.campaigns.id"))
    impressions: Mapped[int] = mapped_column(Integer)
    clicks: Mapped[int] = mapped_column(Integer)
    conversions: Mapped[int] = mapped_column(Integer)

    def __repr__(self) -> str:
        return (
            f"Performance(id={self.id}, campaign_id={self.campaign_id}, impressions={self.impressions}, "
            f"clicks={self.clicks}, conversions={self.conversions})"
        )
