from typing import Any

from pydantic import BaseModel, Field


class ToolExecution(BaseModel):
    tool: str = Field(min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)
    data: Any = None
