import pytest
from app.policy.intent import IntentPolicy


@pytest.fixture
def policy():
    return IntentPolicy()


def test_normalize_valid_intents(policy):
    assert policy.normalize("data_query") == "data_query"
    assert policy.normalize("general") == "general"
    assert policy.normalize("clarification") == "clarification"


def test_normalize_case_insensitive(policy):
    assert policy.normalize("DATA_QUERY") == "data_query"
    assert policy.normalize("General") == "general"


def test_normalize_strips_whitespace(policy):
    assert policy.normalize("  data_query  ") == "data_query"


def test_normalize_unknown_falls_back_to_clarification(policy):
    assert policy.normalize("product_search") == "clarification"
    assert policy.normalize("") == "clarification"
    assert policy.normalize("random garbage") == "clarification"


def test_is_data_intent(policy):
    assert policy.is_data_intent("data_query") is True
    assert policy.is_data_intent("general") is False
    assert policy.is_data_intent("clarification") is False
    assert policy.is_data_intent("unknown") is False
