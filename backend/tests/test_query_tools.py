from app.core.business_policy.query_policy import QueryPolicy
from app.dto.query import QueryPlanV2
from app.services.query_tools import QueryToolFactory


class FakeSchemaService:
    def __init__(self):
        self._schema = {
            "snapshot_hash": "hash-1",
            "snapshot_version": "hash-1",
            "tables": {
                "product.products": {
                    "column_names": ["id", "name", "category", "price", "brand"],
                }
            },
            "relationships": [],
        }

    def get_schema(self, table_name: str | None = None, detail_level: str = "summary"):
        _ = table_name
        _ = detail_level
        return self._schema


class FakeQueryExecutor:
    def __init__(self):
        self.query_policy = QueryPolicy()

    def execute_plan_v2(self, plan: QueryPlanV2, schema_metadata: dict | None = None):
        _ = plan
        _ = schema_metadata
        return [{"id": 1, "name": "Glow Serum"}], "SELECT id, name FROM product.products"


def _query_tool():
    factory = QueryToolFactory(schema_service=FakeSchemaService(), query_executor=FakeQueryExecutor())
    tools = factory.get_tools()
    return next(tool for tool in tools if tool.name == "query_table")


def test_query_table_requires_metadata_hash() -> None:
    tool = _query_tool()
    result = tool.invoke(
        {
            "plan": {
                "source": {"table": "product.products", "alias": "p"},
                "select": [{"field": "p.name"}],
            }
        }
    )

    assert result["error"]["code"] == "metadata_required"


def test_query_table_with_matching_metadata_hash_executes() -> None:
    tool = _query_tool()
    result = tool.invoke(
        {
            "plan": {
                "source": {"table": "product.products", "alias": "p"},
                "select": [{"field": "p.name"}],
                "metadata_hash": "hash-1",
            }
        }
    )

    assert result["query_kind"] == "query_table"
    assert result["join_count"] == 0
    assert result["row_count"] == 1
