from sqlalchemy.orm import Session, Query

from app.models.audience import Audience
from app.repository.base import BaseRepository


class AudienceRepository(BaseRepository[Audience]):
    def __init__(self, db: Session):
        super().__init__(Audience, db)

    def search(
        self,
        name: str | None = None,
        age_range: str | None = None,
        preferences: str | None = None,
    ) -> list[Audience]:
        q: Query = self.db.query(Audience)
        if name:
            q = q.filter(Audience.name.ilike(f"%{name}%"))
        if age_range:
            q = q.filter(Audience.age_range.ilike(f"%{age_range}%"))
        if preferences:
            q = q.filter(Audience.preferences.ilike(f"%{preferences}%"))
        return q.all()
