from langchain_core.tools import tool
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.business_policy.query_policy import QueryPolicy
from app.core.exceptions.base import AppException, BadRequestException
from app.dto.query import QueryPlan
from app.services.schema import SchemaService


def _normalize_error(exc: Exception) -> dict:
    if isinstance(exc, BadRequestException):
        return {"code": "policy_validation_error", "message": exc.detail}
    if isinstance(exc, AppException):
        return {"code": "app_error", "message": exc.detail}
    return {"code": "tool_execution_error", "message": str(exc) or "Tool execution failed"}


def _execute_sql(db: Session, sql: str, query_policy: QueryPolicy) -> list[dict]:
    """Execute read-only SQL with timeout and row-limit guards."""
    timeout_ms = query_policy.statement_timeout_ms
    if timeout_ms > 0:
        try:
            db.execute(text("SET LOCAL statement_timeout = :timeout_ms"), {"timeout_ms": timeout_ms})
        except Exception:
            pass

    result = db.execute(text(sql)).mappings()
    max_rows = max(1, query_policy.max_result_rows)
    rows = result.fetchmany(max_rows + 1)
    if len(rows) > max_rows:
        raise BadRequestException(f"Result set exceeds max_result_rows={max_rows}. Please narrow your query.")
    return [dict(row) for row in rows]


def create_query_table_tool(
    schema_service: SchemaService,
    query_policy: QueryPolicy,
    db: Session,
):
    """Creates the query_table langchain tool with proper dependency injection."""

    @tool
    def query_table(plan: dict) -> dict:
        """Execute a read-only structured query plan.

        The plan must follow QueryPlan and include metadata_hash from lookup_schema.
        """
        try:
            parsed_plan = QueryPlan.model_validate(plan)
        except Exception as exc:
            return {"error": {"code": "invalid_plan_payload", "message": str(exc)}}

        current_schema = schema_service.get_schema(detail_level="summary")
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
            validated_plan = query_policy.validate_plan_v2(parsed_plan, schema_metadata=current_schema)
            allowed_tables = query_policy.resolve_allowed_tables(current_schema)
            sql = query_policy.build_sql(validated_plan, allowed_tables=allowed_tables)
            validated_sql = query_policy.validate_sql(sql, schema_metadata=current_schema)
            rows = _execute_sql(db, validated_sql, query_policy)
        except Exception as exc:
            return {
                "error": _normalize_error(exc),
                "metadata_hash": latest_hash,
                "metadata_version": latest_version,
            }

        return {
            "query_kind": "query_table",
            "join_count": len(validated_plan.joins),
            "subquery_count": len(validated_plan.subqueries),
            "row_count": len(rows),
            "rows": rows,
            "executed_sql": validated_sql,
            "metadata_hash": latest_hash,
            "metadata_version": latest_version,
        }

    return query_table
