from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.services.agent.dto import ToolExecution
from app.services.intent.dto import PredictResponse

ExecutionPath = Literal["direct", "query_table"]


class PredictRequest(BaseModel):
    text: str


class ProcessStep(BaseModel):
    stage: str = Field(min_length=1)
    title: str = Field(min_length=1)
    detail: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class PredictResult(BaseModel):
    input: str = Field(min_length=1)
    extraction: PredictResponse
    mode: ExecutionPath
    tool_results: list[ToolExecution] = Field(default_factory=list)
    process: list[ProcessStep] = Field(default_factory=list)
    message: str = ""
