from sqlalchemy.orm import Session

from app.core.business_policy.query_policy import QueryPolicy
from app.services.schema import SchemaService
from app.services.tools.data_query import create_query_table_tool
from app.services.tools.lookup_schema import create_lookup_schema_tool

TOOL_REGISTRY: dict[str, dict] = {
    "lookup_schema": {
        "description": "Inspect current schema metadata, relationships, and constraints.",
    },
    "query_table": {
        "description": "Execute a structured QueryPlan with metadata_hash validation.",
    },
}


def get_tools(
    schema_service: SchemaService,
    query_policy: QueryPolicy,
    db: Session,
) -> list:
    """Build and return all available langchain tools."""
    return [
        create_lookup_schema_tool(schema_service),
        create_query_table_tool(schema_service, query_policy, db),
    ]
