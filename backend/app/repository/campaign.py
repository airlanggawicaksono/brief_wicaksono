from sqlalchemy.orm import Session, Query

from app.models.campaign import Campaign
from app.repository.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    def __init__(self, db: Session):
        super().__init__(Campaign, db)

    def search(
        self,
        product_id: int | None = None,
        audience_id: int | None = None,
        budget_max: int | None = None,
    ) -> list[Campaign]:
        q: Query = self.db.query(Campaign)
        if product_id:
            q = q.filter(Campaign.product_id == product_id)
        if audience_id:
            q = q.filter(Campaign.audience_id == audience_id)
        if budget_max:
            q = q.filter(Campaign.budget <= budget_max)
        return q.all()
