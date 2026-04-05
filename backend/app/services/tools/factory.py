from sqlalchemy.orm import Session

from app.policy.query import QueryPolicy
from app.services.tools.query import create_query_table_tool
from app.services.tools.schema import SchemaService, create_lookup_schema_tool


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


def build_tool_context(query_policy: QueryPolicy, tools: list) -> str:
    """Build a system message string injected into every agent conversation.

    This is sent as a second SystemMessage (after TOOL_AGENT_PROMPT) so the LLM
    always knows — at runtime — which tools exist and what policy limits apply.

    ## Available tools
    Each line is:  - <tool.name>: <tool.description>
    tool.name        -> the exact string the LLM must use in tool_calls[].name
    tool.description -> the full @tool docstring; this is how the LLM learns
                        what the tool does and when to call it.
                        Write docstrings as instructions TO the LLM.

    ## Query constraints
    Runtime policy values from QueryPolicy. Telling the LLM these directly
    prevents it from generating queries that will be rejected by the policy layer
    (e.g. asking for 10000 rows when max is 100).
    """
    # tool.name and tool.description come from the @tool decorator docstring
    tool_lines = [f"- {t.name}: {t.description}" for t in tools]

    # runtime policy limits — keeps LLM aware of what queries will be allowed
    constraints = [
        f"- max_result_rows: {query_policy.max_result_rows}",
        f"- allow_order_by: {query_policy.allow_order_by}",
        f"- allow_subqueries: {query_policy.allow_subqueries}",
        "- write_operations: disabled (SELECT only)",
    ]
    sections = [
        "## Available tools\n" + "\n".join(tool_lines),
        "## Query constraints\n" + "\n".join(constraints),
    ]
    return "\n\n".join(sections)
