from datetime import UTC, datetime
from typing import Any, Generic, Literal, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums.event_type import Stage, EventType
from app.repository.chat_memory import ChatMessage
from app.services.agent.dto import ToolExecution
from app.services.intent.dto import IntentExtraction

O = TypeVar("O")

ExecutionPath = Literal["direct", "agent"]


class ProcessEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(default_factory=lambda: uuid4().hex)
    type: EventType
    stage: Stage
    title: str
    detail: str = ""
    data: Any = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class StepResult(BaseModel, Generic[O]):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    ok: bool
    output: O | None = None
    events: list[ProcessEvent] = Field(default_factory=list)
    error: dict | None = None


class RequestContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    session_id: str
    text: str
    history: list[ChatMessage] = Field(default_factory=list)
    intent: str | None = None


class PredictRequest(BaseModel):
    text: str


class AgentStepOutput(BaseModel):
    tool_results: list[ToolExecution] = Field(default_factory=list)
    message: str = ""


class PredictResult(BaseModel):
    input: str = Field(min_length=1)
    extraction: IntentExtraction
    mode: ExecutionPath
    tool_results: list[ToolExecution] = Field(default_factory=list)
    process: list[ProcessEvent] = Field(default_factory=list)
    message: str = ""
