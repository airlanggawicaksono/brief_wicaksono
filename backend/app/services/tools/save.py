from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.policy.query import QueryPolicy
from app.repository.workspace import WorkspaceRepository
from app.services.tools.query import _execute_sql, _normalize_error
from app.services.tools.schema import SchemaService


def create_save_result_tool(
    schema_service: SchemaService,
    query_policy: QueryPolicy,
    db: Session,
    workspace_repo: WorkspaceRepository,
    session_id: str,
):
    @tool
    def save_result(name: str, sql: str) -> dict:
        """Save a query result to the session workspace as a named dataset.

        Call this when the user wants to keep data for further analysis or
        visualization in this or a future turn. Pass the exact SQL used in
        the preceding query_table call. The dataset is addressable by name
        for list_workspace and run_python for the lifetime of this session.
        """
        current_schema = schema_service.get_schema(detail_level="summary")
        try:
            validated_sql = query_policy.validate_sql(sql, schema_metadata=current_schema)
            rows = _execute_sql(db, validated_sql, query_policy)
        except Exception as exc:
            return {"error": _normalize_error(exc)}

        workspace_repo.save(session_id, name, rows)
        return {"saved": name, "row_count": len(rows)}

    return save_result


def create_list_workspace_tool(workspace_repo: WorkspaceRepository, session_id: str):
    @tool
    def list_workspace() -> dict:
        """List all datasets currently saved in the session workspace.

        Call this at the start of any turn where the user references previous
        results or asks to build on, compare, or visualize earlier data.
        Returns the names that can be passed to run_python as variables.
        """
        names = workspace_repo.list(session_id)
        return {"datasets": names, "count": len(names)}

    return list_workspace
