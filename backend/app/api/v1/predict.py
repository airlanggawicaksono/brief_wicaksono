from uuid import uuid4
from functools import lru_cache

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.llm_provider import create_llm_provider
from app.policy.intent import IntentPolicy
from app.policy.query import QueryPolicy
from app.policy.tool import ToolPolicy
from app.repository.chat_memory import RedisChatMemory
from app.services.agent import AgentService
from app.services.agent.executor import ToolExecutor
from app.services.agent.message import MessageBuilder
from app.services.intent import IntentService
from app.services.predict import PredictService
from app.services.predict.dto import PredictRequest
from app.services.predict.presenter import SsePresenter
from app.services.predict.steps import AgentStep, DirectResponseStep, IntentStep
from app.services.tools import build_tool_context, get_tools
from app.services.tools.schema import SchemaService

router = APIRouter(prefix="/predict", tags=["predict"])


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


def get_schema_service() -> SchemaService:
    return SchemaService()


def get_query_tools(
    schema_service: SchemaService = Depends(get_schema_service),
    query_policy: QueryPolicy = Depends(get_query_policy),
    db: Session = Depends(get_db),
) -> list:
    return get_tools(schema_service=schema_service, query_policy=query_policy, db=db)


def get_intent_service(
    provider: BaseChatModel = Depends(get_llm_provider),
    intent_policy: IntentPolicy = Depends(get_intent_policy),
) -> IntentService:
    return IntentService(provider=provider, intent_policy=intent_policy)


def get_chat_memory_repository() -> RedisChatMemory:
    return RedisChatMemory()


def get_agent_service(
    provider: BaseChatModel = Depends(get_llm_provider),
    tools: list = Depends(get_query_tools),
    tool_policy: ToolPolicy = Depends(get_tool_policy),
    query_policy: QueryPolicy = Depends(get_query_policy),
) -> AgentService:
    return AgentService(
        provider=provider,
        tool_policy=tool_policy,
        message_builder=MessageBuilder(tool_context=build_tool_context(query_policy)),
        executor=ToolExecutor(tools),
    )


def get_predict_service(
    provider: BaseChatModel = Depends(get_llm_provider),
    intent_service: IntentService = Depends(get_intent_service),
    agent_service: AgentService = Depends(get_agent_service),
    intent_policy: IntentPolicy = Depends(get_intent_policy),
    chat_memory: RedisChatMemory = Depends(get_chat_memory_repository),
) -> PredictService:
    return PredictService(
        intent_step=IntentStep(intent_service, intent_policy),
        agent_step=AgentStep(agent_service),
        direct_step=DirectResponseStep(provider),
        chat_memory=chat_memory,
        presenter=SsePresenter(),
    )


def _resolve_session_id(request: Request) -> str:
    header_id = request.headers.get("X-Session-Id")
    if header_id and header_id.strip():
        return header_id.strip()

    cookie_id = request.cookies.get("session_id")
    if cookie_id and cookie_id.strip():
        return cookie_id.strip()

    return str(uuid4())


@router.post("")
def predict(
    body: PredictRequest,
    request: Request,
    service: PredictService = Depends(get_predict_service),
):
    session_id = _resolve_session_id(request)
    response = StreamingResponse(
        service.run_stream(body.text, session_id=session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id,
        },
    )
    response.set_cookie("session_id", session_id, httponly=False, samesite="lax")
    return response


@router.get("/history")
def get_history(
    request: Request,
    limit: int = 20,
    service: PredictService = Depends(get_predict_service),
):
    session_id = _resolve_session_id(request)
    return service.list_session_history(session_id=session_id, limit=limit)
