from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

QueryOperator = Literal["eq", "ilike", "lt", "lte", "gt", "gte", "in"]
QueryJoinType = Literal["inner", "left", "right"]
SortDirection = Literal["asc", "desc"]
QueryAggregate = Literal["sum", "count", "avg", "min", "max"]

ScalarValue = str | int | float
FilterValue = ScalarValue | list[ScalarValue]


class QueryFilter(BaseModel):
    field: str = Field(min_length=1, description="Column name to filter on")
    op: QueryOperator = Field(default="eq", description="Filter operator")
    value: FilterValue = Field(description="Value used in comparison")

    @field_validator("field")
    @classmethod
    def normalize_field(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("value")
    @classmethod
    def ensure_non_empty_list(cls, value: FilterValue) -> FilterValue:
        if isinstance(value, list) and len(value) == 0:
            raise ValueError("Filter value list cannot be empty")
        return value


class QuerySource(BaseModel):
    table: str = Field(min_length=1)
    alias: str | None = None

    @field_validator("table")
    @classmethod
    def normalize_table(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("alias")
    @classmethod
    def normalize_alias(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None


class QuerySelectItem(BaseModel):
    field: str = Field(min_length=1, description="Column token, e.g. product.products.name or alias.name")
    aggregate: QueryAggregate | None = None
    distinct: bool = False
    alias: str | None = None

    @field_validator("field")
    @classmethod
    def normalize_field(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("alias")
    @classmethod
    def normalize_alias(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None


class QueryJoinItem(BaseModel):
    table: str = Field(min_length=1)
    alias: str | None = None
    left_on: str = Field(min_length=1, description="Field token on current scope, e.g. c.product_id")
    right_on: str = Field(min_length=1, description="Field token on joined table scope, e.g. p.id")
    join_type: QueryJoinType = "inner"

    @field_validator("table", "left_on", "right_on")
    @classmethod
    def normalize_tokens(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("alias")
    @classmethod
    def normalize_alias(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None


class QueryOrderItem(BaseModel):
    field: str = Field(min_length=1)
    direction: SortDirection = "asc"

    @field_validator("field")
    @classmethod
    def normalize_field(cls, value: str) -> str:
        return value.strip().lower()


class QuerySubquery(BaseModel):
    alias: str = Field(min_length=1)
    plan: "QueryPlanV2"
    join_on_left: str = Field(min_length=1)
    join_on_right: str = Field(min_length=1)
    join_type: QueryJoinType = "inner"

    @field_validator("alias", "join_on_left", "join_on_right")
    @classmethod
    def normalize_tokens(cls, value: str) -> str:
        return value.strip().lower()


class QueryPlanV2(BaseModel):
    source: QuerySource
    select: list[QuerySelectItem] = Field(default_factory=list)
    joins: list[QueryJoinItem] = Field(default_factory=list)
    filters: list[QueryFilter] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    order_by: list[QueryOrderItem] = Field(default_factory=list)
    subqueries: list[QuerySubquery] = Field(default_factory=list)
    limit: int | None = Field(default=None, ge=1)
    offset: int | None = Field(default=None, ge=0)
    metadata_hash: str | None = None

    @field_validator("group_by")
    @classmethod
    def normalize_group_by(cls, value: list[str]) -> list[str]:
        return [item.strip().lower() for item in value if item and item.strip()]

    @field_validator("metadata_hash")
    @classmethod
    def normalize_hash(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None

    @model_validator(mode="after")
    def validate_shape(self):
        if not self.select:
            self.select = [QuerySelectItem(field="*")]
        return self


QueryPlanV2.model_rebuild()
