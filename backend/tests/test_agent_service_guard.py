from app.services.agent.service import AgentService


def test_force_concrete_fetch_when_only_schema_used_for_non_technical_data_query():
    service = AgentService.__new__(AgentService)
    assert service._should_force_concrete_data_fetch(
        intent="data_query",
        user_text="what are the audience segments?",
        used_lookup_schema=True,
        used_data_fetch=False,
        already_forced=False,
    )


def test_do_not_force_concrete_fetch_for_technical_structure_request():
    service = AgentService.__new__(AgentService)
    assert not service._should_force_concrete_data_fetch(
        intent="data_query",
        user_text="what columns are in product.audiences table?",
        used_lookup_schema=True,
        used_data_fetch=False,
        already_forced=False,
    )


def test_do_not_force_when_data_already_fetched():
    service = AgentService.__new__(AgentService)
    assert not service._should_force_concrete_data_fetch(
        intent="data_query",
        user_text="show campaigns",
        used_lookup_schema=True,
        used_data_fetch=True,
        already_forced=False,
    )
