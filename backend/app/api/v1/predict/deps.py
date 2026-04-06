from functools import lru_cache
from uuid import uuid4

from fastapi import Depends, Request
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.llm_provider import create_llm_provider
from app.policy.intent import IntentPolicy
from app.policy.query import QueryPolicy
from app.policy.tool import ToolPolicy
from app.repository.chat_memory import RedisChatMemory
from app.repository.workspace import WorkspaceRepository
from app.services.agent import AgentService
from app.services.intent import IntentService
from app.services.predict import PredictService
from app.services.tools import get_tools
from app.services.tools.schema import SchemaService


# ── singletons ──────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_llm_provider() -> BaseChatModel:
    return create_llm_provider()


@lru_cache(maxsize=1)
def get_query_policy() -> QueryPolicy:
    return QueryPolicy()


@lru_cache(maxsize=1)
def get_intent_policy() -> IntentPolicy:
    return IntentPolicy()


@lru_cache(maxsize=1)
def get_tool_policy() -> ToolPolicy:
    return ToolPolicy()


# ── per-request infrastructure ──────────────────────────────


def get_schema_service() -> SchemaService:
    return SchemaService()


def get_workspace_repository() -> WorkspaceRepository:
    return WorkspaceRepository()


def get_chat_memory_repository() -> RedisChatMemory:
    return RedisChatMemory()


def get_session_id(request: Request) -> str:
    header_id = request.headers.get("X-Session-Id")
    if header_id and header_id.strip():
        return header_id.strip()
    cookie_id = request.cookies.get("session_id")
    if cookie_id and cookie_id.strip():
        return cookie_id.strip()
    return str(uuid4())


def get_query_tools(
    schema_service: SchemaService = Depends(get_schema_service),
    query_policy: QueryPolicy = Depends(get_query_policy),
    db: Session = Depends(get_db),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
    session_id: str = Depends(get_session_id),
) -> list:
    return get_tools(
        schema_service=schema_service,
        query_policy=query_policy,
        db=db,
        workspace_repo=workspace_repo,
        session_id=session_id,
    )


# ── services ────────────────────────────────────────────────


def get_intent_service(
    provider: BaseChatModel = Depends(get_llm_provider),
    intent_policy: IntentPolicy = Depends(get_intent_policy),
) -> IntentService:
    return IntentService(provider=provider, intent_policy=intent_policy)


def get_agent_service(
    provider: BaseChatModel = Depends(get_llm_provider),
    tools: list = Depends(get_query_tools),
    tool_policy: ToolPolicy = Depends(get_tool_policy),
    query_policy: QueryPolicy = Depends(get_query_policy),
) -> AgentService:
    return AgentService(
        provider=provider,
        tool_policy=tool_policy,
        tools=tools,
        query_policy=query_policy,
    )


def get_predict_service(
    intent_service: IntentService = Depends(get_intent_service),
    intent_policy: IntentPolicy = Depends(get_intent_policy),
    agent_service: AgentService = Depends(get_agent_service),
    provider: BaseChatModel = Depends(get_llm_provider),
    chat_memory: RedisChatMemory = Depends(get_chat_memory_repository),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
) -> PredictService:
    return PredictService(
        intent_service=intent_service,
        intent_policy=intent_policy,
        agent_service=agent_service,
        provider=provider,
        chat_memory=chat_memory,
        workspace_repo=workspace_repo,
    )
