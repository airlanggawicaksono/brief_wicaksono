from functools import lru_cache
from typing import Literal

from langchain_core.tools import tool

from app.config.database import ORM_BASES
from app.services.tools.dto import (
    ColumnMetadata,
    ForeignKeyMetadata,
    SchemaMetadataResponse,
    TableMetadata,
)


@lru_cache(maxsize=1)
def _build_full_schema() -> SchemaMetadataResponse:
    """Build and cache schema metadata from all registered ORM bases.

    Runs once per process. ORM metadata is static after startup so caching
    is safe and avoids re-introspecting on every agent tool call.
    To expose a new schema to the agent, add it to ORM_BASES in database.py.
    """
    schema: dict[str, TableMetadata] = {}
    relationships: list[ForeignKeyMetadata] = []

    for label, base in ORM_BASES:
        for mapper in base.registry.mappers:
            table = mapper.class_.__table__
            table_schema = table.schema or label
            table_key = f"{table_schema}.{table.name}"

            columns: list[ColumnMetadata] = []
            foreign_keys: list[ForeignKeyMetadata] = []

            for col in table.columns:
                columns.append(
                    ColumnMetadata(
                        name=col.name,
                        type=str(col.type),
                        nullable=col.nullable,
                        primary_key=col.primary_key,
                        indexed=bool(col.index),
                        max_length=getattr(col.type, "length", None),
                    )
                )
                for fk in col.foreign_keys:
                    target_column = fk.column
                    target_table = target_column.table
                    fk_meta = ForeignKeyMetadata(
                        source_schema=table_schema,
                        source_table=table.name,
                        source_column=col.name,
                        target_schema=target_table.schema,
                        target_table=target_table.name,
                        target_column=target_column.name,
                        target_fullname=fk.target_fullname,
                    )
                    foreign_keys.append(fk_meta)
                    relationships.append(fk_meta)

            schema[table_key] = TableMetadata(
                domain=label,
                schema=table_schema,
                table=table.name,
                column_count=len(columns),
                columns=columns,
                column_names=[c.name for c in columns],
                foreign_keys=foreign_keys,
            )

    return SchemaMetadataResponse(tables=schema, relationships=relationships)


class SchemaService:
    """Introspects ORM registry and returns schema metadata.

    Schema is built once on first access and cached for the process lifetime.
    Only tables registered in ORM_BASES (database.py) are visible to the agent.
    """

    def get_schema(
        self,
        table_name: str | None = None,
        detail_level: Literal["summary", "full"] = "summary",
    ) -> dict:
        schema_response = _build_full_schema()

        if table_name:
            normalized = table_name.strip().lower()
            matches = {k: v for k, v in schema_response.tables.items() if normalized in k}
            if matches:
                filtered = SchemaMetadataResponse(
                    tables=matches,
                    relationships=[
                        rel
                        for rel in schema_response.relationships
                        if f"{rel.source_schema}.{rel.source_table}" in matches
                        or f"{rel.target_schema}.{rel.target_table}" in matches
                    ],
                )
                return self._format_schema_dump(filtered.model_dump(), detail_level)
            return {"error": f"Table '{table_name}' not found. Available: {list(schema_response.tables.keys())}"}

        return self._format_schema_dump(schema_response.model_dump(), detail_level)

    def _format_schema_dump(self, schema_dump: dict, detail_level: Literal["summary", "full"]) -> dict:
        if detail_level == "full":
            return schema_dump

        tables = schema_dump.get("tables", {})
        summary_tables: dict[str, dict] = {}
        for table_key, table_meta in tables.items():
            if not isinstance(table_meta, dict):
                continue
            summary_tables[table_key] = {
                "domain": table_meta.get("domain"),
                "schema": table_meta.get("schema"),
                "table": table_meta.get("table"),
                "column_count": table_meta.get("column_count"),
                "column_names": table_meta.get("column_names"),
                "foreign_keys": [
                    {
                        "source": f"{fk.get('source_schema')}.{fk.get('source_table')}.{fk.get('source_column')}",
                        "target": f"{fk.get('target_schema')}.{fk.get('target_table')}.{fk.get('target_column')}",
                    }
                    for fk in table_meta.get("foreign_keys", [])
                    if isinstance(fk, dict)
                ],
            }

        return {
            "table_count": len(summary_tables),
            "tables": summary_tables,
            "relationships": [
                {
                    "source": f"{rel.get('source_schema')}.{rel.get('source_table')}.{rel.get('source_column')}",
                    "target": f"{rel.get('target_schema')}.{rel.get('target_table')}.{rel.get('target_column')}",
                }
                for rel in schema_dump.get("relationships", [])
                if isinstance(rel, dict)
            ],
        }


def create_lookup_schema_tool(schema_service: SchemaService):

    @tool
    def lookup_schema(
        table_name: str | None = None,
        detail_level: str = "summary",
    ) -> dict:
        """Inspect schema metadata and query constraints before planning a query.

        Always call this before query_table to see available tables, columns, and relationships.
        """
        normalized_detail = detail_level.lower().strip()
        detail: Literal["summary", "full"] = "summary"
        if normalized_detail == "full":
            detail = "full"
        return schema_service.get_schema(table_name=table_name, detail_level=detail)

    return lookup_schema
