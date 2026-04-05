from langchain_core.tools import tool
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, BadRequestException
from app.policy.query import QueryPolicy
from app.services.tools.schema import SchemaService


def _normalize_error(exc: Exception) -> dict:
    if isinstance(exc, BadRequestException):
        return {"code": "policy_validation_error", "message": exc.detail}
    if isinstance(exc, AppException):
        return {"code": "app_error", "message": exc.detail}
    return {"code": "query_error", "message": str(exc) or "Query execution failed"}


def _execute_sql(db: Session, sql: str, query_policy: QueryPolicy) -> list[dict]:
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

    @tool
    def query_table(sql: str) -> dict:
        """Execute a read-only SQL SELECT query against the database.

        Write standard PostgreSQL SELECT queries using schema-qualified table names.
        Call lookup_schema first to discover available tables and columns.
        """
        current_schema = schema_service.get_schema(detail_level="summary")

        try:
            validated_sql = query_policy.validate_sql(sql, schema_metadata=current_schema)
            rows = _execute_sql(db, validated_sql, query_policy)
        except Exception as exc:
            return {"error": _normalize_error(exc)}

        return {
            "row_count": len(rows),
            "rows": rows,
            "executed_sql": validated_sql,
        }

    return query_table
