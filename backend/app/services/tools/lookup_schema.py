from typing import Literal

from langchain_core.tools import tool

from app.services.schema import SchemaService


def create_lookup_schema_tool(schema_service: SchemaService):
    """Creates the lookup_schema langchain tool bound to a SchemaService instance."""

    @tool
    def lookup_schema(
        table_name: str | None = None,
        detail_level: str = "summary",
    ) -> dict:
        """Inspect schema metadata and query constraints before planning a query.

        Always call this before query_table and pass snapshot_hash back in QueryPlan.metadata_hash.
        """
        normalized_detail = detail_level.lower().strip()
        detail: Literal["summary", "full"] = "summary"
        if normalized_detail == "full":
            detail = "full"
        return schema_service.get_schema(table_name=table_name, detail_level=detail)

    return lookup_schema
