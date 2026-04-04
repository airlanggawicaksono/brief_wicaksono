import pytest

from app.core.business_policy.query_policy import QueryPolicy
from app.core.exceptions.base import BadRequestException
from app.dto.query import QueryPlanV2


def _metadata() -> dict:
    return {
        "tables": {
            "product.products": {"column_names": ["id", "name", "category", "price", "brand"]},
            "marketing.campaigns": {"column_names": ["id", "name", "product_id", "audience_id", "budget"]},
        },
        "relationships": [
            {
                "source": "marketing.campaigns.product_id",
                "target": "product.products.id",
            }
        ],
    }


def test_validate_plan_v2_allows_valid_join_and_order() -> None:
    policy = QueryPolicy()
    plan = QueryPlanV2.model_validate(
        {
            "source": {"table": "marketing.campaigns", "alias": "c"},
            "select": [{"field": "c.name"}, {"field": "c.budget"}],
            "joins": [
                {
                    "table": "product.products",
                    "alias": "p",
                    "left_on": "c.product_id",
                    "right_on": "p.id",
                    "join_type": "inner",
                }
            ],
            "order_by": [{"field": "c.budget", "direction": "desc"}],
            "metadata_hash": "abc123",
        }
    )

    validated = policy.validate_plan_v2(plan, schema_metadata=_metadata())
    assert validated.source.table == "marketing.campaigns"


def test_validate_plan_v2_rejects_unknown_column_from_metadata() -> None:
    policy = QueryPolicy()
    plan = QueryPlanV2.model_validate(
        {
            "source": {"table": "marketing.campaigns", "alias": "c"},
            "select": [{"field": "c.total_conversions"}],
            "metadata_hash": "abc123",
        }
    )

    with pytest.raises(BadRequestException) as exc:
        policy.validate_plan_v2(plan, schema_metadata=_metadata())

    assert "not allowed" in exc.value.detail.lower()
