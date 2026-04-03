from langchain_core.tools import tool

from app.core.config.database import Base
from app.repository.product import ProductRepository
from app.repository.audience import AudienceRepository
from app.repository.campaign import CampaignRepository
from app.repository.performance import PerformanceRepository


def _get_schema() -> dict:
    """Derive schema from SQLAlchemy models — single source of truth."""
    schema = {}
    for mapper in Base.registry.mappers:
        model = mapper.class_
        table = model.__table__
        columns = [col.name for col in table.columns]
        fks = [
            f"{col.name} -> {list(col.foreign_keys)[0].target_fullname}"
            for col in table.columns if col.foreign_keys
        ]
        schema[table.name] = {
            "columns": columns,
            "foreign_keys": fks,
        }
    return schema


def create_tools(
    product_repo: ProductRepository,
    audience_repo: AudienceRepository,
    campaign_repo: CampaignRepository,
    performance_repo: PerformanceRepository,
) -> list:
    """Factory: expose DB schema + query tools for LLM."""

    @tool
    def lookup_schema(table_name: str | None = None) -> dict:
        """Look up the available database schema. Call this FIRST when you need to understand
        what data is available, what tables exist, or how they relate to each other.
        Pass a table_name to get details for a specific table, or omit it to get all tables."""
        schema = _get_schema()
        if table_name:
            info = schema.get(table_name)
            if info:
                return {table_name: info}
            return {"error": f"Table '{table_name}' not found. Available: {list(schema.keys())}"}
        return schema

    @tool
    def search_products(
        category: str | None = None,
        brand: str | None = None,
        price_max: int | None = None,
    ) -> list[dict]:
        """Search products table. Columns: id, name, category, price, brand.
        Use when the user asks about products, items, or goods."""
        products = product_repo.search(category=category, brand=brand, price_max=price_max)
        return [{"id": p.id, "name": p.name, "category": p.category, "price": p.price, "brand": p.brand} for p in products]

    @tool
    def search_audiences(
        name: str | None = None,
        age_range: str | None = None,
        preferences: str | None = None,
    ) -> list[dict]:
        """Search audiences table. Columns: id, name, age_range, preferences.
        Use when the user asks about target audiences, demographics, or customer segments."""
        audiences = audience_repo.search(name=name, age_range=age_range, preferences=preferences)
        return [{"id": a.id, "name": a.name, "age_range": a.age_range, "preferences": a.preferences} for a in audiences]

    @tool
    def search_campaigns(
        product_id: int | None = None,
        audience_id: int | None = None,
        budget_max: int | None = None,
    ) -> list[dict]:
        """Search campaigns table. Columns: id, name, product_id, audience_id, budget.
        Use when the user asks about marketing campaigns or ad budgets."""
        campaigns = campaign_repo.search(product_id=product_id, audience_id=audience_id, budget_max=budget_max)
        return [{"id": c.id, "name": c.name, "product_id": c.product_id, "audience_id": c.audience_id, "budget": c.budget} for c in campaigns]

    @tool
    def get_campaign_performance(campaign_id: int) -> list[dict]:
        """Get performance metrics for a campaign. Columns: id, campaign_id, impressions, clicks, conversions.
        Use when the user asks about campaign results, metrics, CTR, or conversion rates."""
        perfs = performance_repo.get_by_campaign(campaign_id)
        return [{"id": p.id, "campaign_id": p.campaign_id, "impressions": p.impressions, "clicks": p.clicks, "conversions": p.conversions} for p in perfs]

    return [lookup_schema, search_products, search_audiences, search_campaigns, get_campaign_performance]
