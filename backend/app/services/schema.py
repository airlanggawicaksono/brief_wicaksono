from typing import Literal
import hashlib
import json

from app.core.business_policy.query_policy import QueryPolicy
from app.core.config.database import MarketingBase, ProductBase
from app.dto.schema_metadata import (
    ColumnMetadata,
    ForeignKeyMetadata,
    QueryToolMetadata,
    SchemaConstraintsMetadata,
    SchemaMetadataResponse,
    TableMetadata,
)


class SchemaService:
    """Introspects ORM registry and returns policy-aware schema metadata."""

    def __init__(self, query_policy: QueryPolicy):
        self.query_policy = query_policy

    def get_schema(
        self,
        table_name: str | None = None,
        detail_level: Literal["summary", "full"] = "summary",
    ) -> dict:
        schema: dict[str, TableMetadata] = {}
        relationships: list[ForeignKeyMetadata] = []

        for label, base in [("product", ProductBase), ("marketing", MarketingBase)]:
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
                    column_names=[column.name for column in columns],
                    foreign_keys=foreign_keys,
                )

        raw_tables_dump = {table_key: table_meta.model_dump() for table_key, table_meta in schema.items()}
        snapshot_hash = hashlib.sha256(
            json.dumps(raw_tables_dump, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        schema_response = SchemaMetadataResponse(
            snapshot_hash=snapshot_hash,
            snapshot_version=snapshot_hash[:12],
            tables=schema,
            query_tools={
                "lookup_schema": QueryToolMetadata(
                    description="Inspect current schema metadata, relationships, and constraints.",
                ),
                "query_table": QueryToolMetadata(
                    description="Execute a structured QueryPlan with metadata_hash validation.",
                ),
            },
            constraints=SchemaConstraintsMetadata(
                allowed_operators=sorted(self.query_policy.allowed_operators),
                allowed_joins=sorted([f"{left} -> {right}" for left, right in self.query_policy.allowed_join_edges]),
                write_operations="disabled",
            ),
            relationships=relationships,
        )

        if table_name:
            normalized = table_name.strip().lower()
            matches = {k: v for k, v in schema_response.tables.items() if normalized in k}
            if matches:
                filtered = SchemaMetadataResponse(
                    snapshot_hash=schema_response.snapshot_hash,
                    snapshot_version=schema_response.snapshot_version,
                    tables=matches,
                    query_tools=schema_response.query_tools,
                    constraints=schema_response.constraints,
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

    def get_snapshot_hash(self) -> str:
        schema = self.get_schema(detail_level="summary")
        value = schema.get("snapshot_hash")
        return value if isinstance(value, str) else ""

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
            "snapshot_hash": schema_dump.get("snapshot_hash"),
            "snapshot_version": schema_dump.get("snapshot_version"),
            "table_count": len(summary_tables),
            "tables": summary_tables,
            "query_tools": schema_dump.get("query_tools", {}),
            "constraints": schema_dump.get("constraints", {}),
            "relationships": [
                {
                    "source": f"{rel.get('source_schema')}.{rel.get('source_table')}.{rel.get('source_column')}",
                    "target": f"{rel.get('target_schema')}.{rel.get('target_table')}.{rel.get('target_column')}",
                }
                for rel in schema_dump.get("relationships", [])
                if isinstance(rel, dict)
            ],
        }
