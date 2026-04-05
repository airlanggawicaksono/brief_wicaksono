from sqlalchemy.orm import Session

from app.policy.query import QueryPolicy
from app.services.tools.query import create_query_table_tool
from app.services.tools.schema import SchemaService, create_lookup_schema_tool

TOOL_REGISTRY: dict[str, dict] = {
    "lookup_schema": {
        "description": "Inspect current schema metadata, relationships, and constraints.",
    },
    "query_table": {
        "description": "Execute a read-only SQL SELECT query against the database.",
    },
    # "pandas_subprocess": {
    #     "description": "Execute subprocess code basedon  pandas library."
    # },
    # "save_table":{
    #     "description": "Save queried in memory data into csv on subprocess. "
    # }
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


def build_tool_context(query_policy: QueryPolicy) -> str:
    """Build dynamic LLM context from tool registry and policy constraints."""
    sections: list[str] = []

    tool_lines = [f"- {name}: {meta['description']}" for name, meta in TOOL_REGISTRY.items()]
    sections.append("## Available tools\n" + "\n".join(tool_lines))

    constraints = [
        f"- max_result_rows: {query_policy.max_result_rows}",
        f"- allow_order_by: {query_policy.allow_order_by}",
        f"- allow_subqueries: {query_policy.allow_subqueries}",
        "- write_operations: disabled (SELECT only)",
    ]
    sections.append("## Query constraints\n" + "\n".join(constraints))

    return "\n\n".join(sections)
