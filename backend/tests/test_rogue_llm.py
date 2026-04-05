"""
Tests for when the LLM produces unexpected, malformed, or adversarial output.
None of these require a real LLM, DB, or Redis connection.
"""
import pytest
from app.policy.query import QueryPolicy
from app.policy.tool import ToolPolicy
from app.core.exceptions import BadRequestException


SCHEMA = {
    "tables": {
        "product.products": {
            "column_names": ["id", "name", "category", "price", "brand"]
        },
        "marketing.campaigns": {
            "column_names": ["id", "name", "product_id", "audience_id", "budget"]
        },
    }
}


@pytest.fixture
def policy():
    return QueryPolicy()


# ── SQL injection / adversarial SQL ───────────────────────────────────────────

def test_multi_statement_blocked(policy):
    """LLM tries to sneak a second statement after a valid SELECT."""
    with pytest.raises(BadRequestException):
        policy.validate_sql(
            "SELECT name FROM product.products; DROP TABLE product.products",
            SCHEMA,
        )


def test_union_into_system_table_blocked(policy):
    """LLM tries UNION to exfiltrate from pg_user or similar."""
    with pytest.raises(BadRequestException):
        policy.validate_sql(
            "SELECT name FROM product.products UNION SELECT usename FROM pg_user",
            SCHEMA,
        )


def test_sql_comment_does_not_bypass(policy):
    """Inline comment after valid SQL should still be parsed and validated correctly."""
    result = policy.validate_sql(
        "SELECT name FROM product.products -- this is fine",
        SCHEMA,
    )
    assert "product.products" in result.lower()


def test_information_schema_blocked(policy):
    """LLM tries to read information_schema to discover tables."""
    with pytest.raises(BadRequestException, match="not allowed"):
        policy.validate_sql(
            "SELECT table_name FROM information_schema.tables",
            SCHEMA,
        )


def test_pg_catalog_blocked(policy):
    """LLM tries to access pg_catalog system tables."""
    with pytest.raises(BadRequestException, match="not allowed"):
        policy.validate_sql(
            "SELECT relname FROM pg_catalog.pg_class",
            SCHEMA,
        )


def test_select_star_allowed_but_from_unknown_table_blocked(policy):
    """LLM uses SELECT * but targets an unknown table."""
    with pytest.raises(BadRequestException, match="not allowed"):
        policy.validate_sql("SELECT * FROM public.secrets", SCHEMA)


# ── resolve_allowed_tables with garbage schema ────────────────────────────────

def test_empty_schema_returns_empty(policy):
    assert policy.resolve_allowed_tables({}) == {}


def test_schema_tables_not_dict_returns_empty(policy):
    assert policy.resolve_allowed_tables({"tables": "not a dict"}) == {}


def test_schema_table_with_no_columns_skipped(policy):
    result = policy.resolve_allowed_tables({
        "tables": {
            "product.products": {"column_names": []},
        }
    })
    assert result == {}


def test_schema_table_with_null_columns_skipped(policy):
    result = policy.resolve_allowed_tables({
        "tables": {
            "product.products": {"column_names": None},
        }
    })
    assert result == {}


# ── ToolPolicy allowlist ───────────────────────────────────────────────────────

@pytest.fixture
def tool_policy():
    return ToolPolicy()


def test_data_query_allows_schema_and_query(tool_policy):
    allowed = tool_policy.allowed_tools_for_intent("data_query")
    assert "lookup_schema" in allowed
    assert "query_table" in allowed


def test_general_intent_allows_no_tools(tool_policy):
    allowed = tool_policy.allowed_tools_for_intent("general")
    assert allowed == set()


def test_clarification_intent_allows_no_tools(tool_policy):
    allowed = tool_policy.allowed_tools_for_intent("clarification")
    assert allowed == set()


def test_unknown_intent_allows_no_tools(tool_policy):
    """LLM produces a completely unknown intent — no tools should be exposed."""
    allowed = tool_policy.allowed_tools_for_intent("hack_the_planet")
    assert allowed == set()
