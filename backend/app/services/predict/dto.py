from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.services.agent.dto import ToolExecution
from app.services.intent.dto import PredictResponse
from app.core.enums.EventType import Stage, EventType

O = TypeVar("O")

ExecutionPath = Literal["direct", "query_table"]


class ProcessEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
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
    history: list[dict] = Field(default_factory=list)
    intent: str | None = None


class PredictRequest(BaseModel):
    text: str


class PredictResult(BaseModel):
    input: str = Field(min_length=1)
    extraction: PredictResponse
    mode: ExecutionPath
    tool_results: list[ToolExecution] = Field(default_factory=list)
    process: list[ProcessEvent] = Field(default_factory=list)
    message: str = ""
