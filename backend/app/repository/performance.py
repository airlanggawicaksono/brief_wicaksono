from sqlalchemy.orm import Session

from app.models.performance import Performance
from app.repository.base import BaseRepository


class PerformanceRepository(BaseRepository[Performance]):
    def __init__(self, db: Session):
        super().__init__(Performance, db)

    def get_by_campaign(self, campaign_id: int) -> list[Performance]:
        return (
            self.db.query(Performance)
            .filter(Performance.campaign_id == campaign_id)
            .all()
        )
