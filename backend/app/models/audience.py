from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config.database import Base


class Audience(Base):
    __tablename__ = "audiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    age_range: Mapped[str] = mapped_column(String(50))
    preferences: Mapped[str] = mapped_column(String(500))
