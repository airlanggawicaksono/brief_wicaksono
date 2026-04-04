from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.dto.response import PredictResponse

ExecutionPath = Literal["direct", "query_table"]


class ToolExecution(BaseModel):
    tool: str = Field(min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)
    data: Any = None


class ProcessStep(BaseModel):
    stage: str = Field(min_length=1)
    title: str = Field(min_length=1)
    detail: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class PredictResult(BaseModel):
    pipeline_version: Literal[2, 3, 4] = 4
    input: str = Field(min_length=1)
    extraction: PredictResponse
    mode: ExecutionPath
    tool_results: list[ToolExecution] = Field(default_factory=list)
    process: list[ProcessStep] = Field(default_factory=list)
    message: str = ""
    metadata_snapshot_hash: str | None = None
    metadata_snapshot_version: str | None = None
