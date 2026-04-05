from typing import Literal

from langchain_core.tools import tool

from app.core.exceptions.base import AppException, BadRequestException
from app.dto.query import QueryPlan
from app.services.query_executor import QueryExecutor
from app.services.schema import SchemaService


class QueryToolFactory:
    """Builds langchain @tool wrappers for metadata-first, policy-validated querying."""

    def __init__(self, schema_service: SchemaService, query_executor: QueryExecutor):
        self.schema_service = schema_service
        self.query_executor = query_executor

    def get_tools(self) -> list:
        schema_svc = self.schema_service
        executor = self.query_executor

        def normalize_error(exc: Exception) -> dict:
            if isinstance(exc, BadRequestException):
                return {"code": "policy_validation_error", "message": exc.detail}
            if isinstance(exc, AppException):
                return {"code": "app_error", "message": exc.detail}
            return {"code": "tool_execution_error", "message": str(exc) or "Tool execution failed"}

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
            return schema_svc.get_schema(table_name=table_name, detail_level=detail)

        @tool
        def query_table(plan: dict) -> dict:
            """Execute a read-only structured query plan.

            The plan must follow QueryPlan and include metadata_hash from lookup_schema.
            """
            try:
                parsed_plan = QueryPlan.model_validate(plan)
            except Exception as exc:
                return {"error": {"code": "invalid_plan_payload", "message": str(exc)}}

            current_schema = schema_svc.get_schema(detail_level="summary")
            latest_hash = current_schema.get("snapshot_hash") if isinstance(current_schema, dict) else None
            latest_version = current_schema.get("snapshot_version") if isinstance(current_schema, dict) else None
            if not parsed_plan.metadata_hash:
                return {
                    "error": {
                        "code": "metadata_required",
                        "message": "metadata_hash is required. Call lookup_schema first and pass snapshot_hash.",
                    },
                    "latest_metadata_hash": latest_hash,
                }

            if parsed_plan.metadata_hash != latest_hash:
                return {
                    "error": {
                        "code": "stale_metadata_hash",
                        "message": "metadata_hash is stale. Call lookup_schema again and re-plan.",
                    },
                    "expected_metadata_hash": latest_hash,
                    "received_metadata_hash": parsed_plan.metadata_hash,
                }

            try:
                validated_plan = executor.query_policy.validate_plan_v2(
                    parsed_plan,
                    schema_metadata=current_schema,
                )
                rows, executed_sql = executor.execute_plan_v2(
                    validated_plan,
                    schema_metadata=current_schema,
                )
            except Exception as exc:
                return {
                    "error": normalize_error(exc),
                    "metadata_hash": latest_hash,
                    "metadata_version": latest_version,
                }

            return {
                "query_kind": "query_table",
                "join_count": len(validated_plan.joins),
                "subquery_count": len(validated_plan.subqueries),
                "row_count": len(rows),
                "rows": rows,
                "executed_sql": executed_sql,
                "metadata_hash": latest_hash,
                "metadata_version": latest_version,
            }

        return [lookup_schema, query_table]
