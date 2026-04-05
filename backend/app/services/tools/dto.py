from pydantic import BaseModel, Field


class ColumnMetadata(BaseModel):
    name: str
    type: str
    nullable: bool
    primary_key: bool
    indexed: bool
    max_length: int | None = None


class ForeignKeyMetadata(BaseModel):
    source_schema: str
    source_table: str
    source_column: str
    target_schema: str | None = None
    target_table: str
    target_column: str
    target_fullname: str


class TableMetadata(BaseModel):
    domain: str
    schema_name: str = Field(alias="schema")
    table: str
    column_count: int
    columns: list[ColumnMetadata] = Field(default_factory=list)
    column_names: list[str] = Field(default_factory=list)
    foreign_keys: list[ForeignKeyMetadata] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "serialize_by_alias": True,
    }


class SchemaMetadataResponse(BaseModel):
    tables: dict[str, TableMetadata] = Field(default_factory=dict)
    relationships: list[ForeignKeyMetadata] = Field(default_factory=list)
