import pytest
from app.policy.query import QueryPolicy
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


def test_valid_select_passes(policy):
    sql = "SELECT name, price FROM product.products"
    result = policy.validate_sql(sql, SCHEMA)
    assert "SELECT" in result.upper()


def test_insert_blocked(policy):
    with pytest.raises(BadRequestException, match="Only SELECT"):
        policy.validate_sql("INSERT INTO product.products (name) VALUES ('x')", SCHEMA)


def test_update_blocked(policy):
    with pytest.raises(BadRequestException, match="Only SELECT"):
        policy.validate_sql("UPDATE product.products SET price = 0", SCHEMA)


def test_delete_blocked(policy):
    with pytest.raises(BadRequestException, match="Only SELECT"):
        policy.validate_sql("DELETE FROM product.products", SCHEMA)


def test_drop_blocked(policy):
    with pytest.raises(BadRequestException, match="Only SELECT"):
        policy.validate_sql("DROP TABLE product.products", SCHEMA)


def test_unknown_table_blocked(policy):
    with pytest.raises(BadRequestException, match="not allowed"):
        policy.validate_sql("SELECT id FROM public.users", SCHEMA)


def test_unknown_column_blocked(policy):
    with pytest.raises(BadRequestException, match="not allowed"):
        policy.validate_sql("SELECT secret_column FROM product.products", SCHEMA)


def test_order_by_blocked_when_disabled(policy):
    strict = QueryPolicy(allow_order_by=False)
    with pytest.raises(BadRequestException, match="ORDER BY"):
        strict.validate_sql("SELECT name FROM product.products ORDER BY price", SCHEMA)


def test_subquery_blocked_when_disabled(policy):
    strict = QueryPolicy(allow_subqueries=False)
    with pytest.raises(BadRequestException, match="Subqueries"):
        strict.validate_sql(
            "SELECT name FROM product.products WHERE id IN (SELECT id FROM product.products)",
            SCHEMA,
        )


def test_unqualified_table_auto_qualified(policy):
    result = policy.validate_sql("SELECT name FROM products", SCHEMA)
    assert "product.products" in result.lower()


def test_invalid_sql_syntax(policy):
    with pytest.raises(BadRequestException, match="Invalid SQL"):
        policy.validate_sql("SELECT FROM WHERE", SCHEMA)
