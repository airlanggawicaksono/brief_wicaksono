from dataclasses import dataclass

from app.core.exceptions import BadRequestException


@dataclass(frozen=True)
class QueryPolicy:
    """Business policy for safe, read-only SQL querying validated via sqlglot."""

    allow_order_by: bool = True
    allow_subqueries: bool = True

    statement_timeout_ms: int = 8_000
    max_result_rows: int = 2_000

    def resolve_allowed_tables(self, schema_metadata: dict) -> dict[str, set[str]]:
        """Derive allowlisted tables/columns from schema metadata."""
        tables_payload = schema_metadata.get("tables")
        if not isinstance(tables_payload, dict):
            return {}

        resolved: dict[str, set[str]] = {}
        for table_key, table_meta in tables_payload.items():
            if not isinstance(table_key, str) or not isinstance(table_meta, dict):
                continue

            raw_names = table_meta.get("column_names")
            if not isinstance(raw_names, list):
                raw_columns = table_meta.get("columns")
                if isinstance(raw_columns, list):
                    raw_names = [
                        col["name"] for col in raw_columns
                        if isinstance(col, dict) and isinstance(col.get("name"), str)
                    ]

            if not isinstance(raw_names, list):
                continue

            normalized_names = {name.strip().lower() for name in raw_names if isinstance(name, str) and name.strip()}
            if normalized_names:
                resolved[table_key.strip().lower()] = normalized_names

        return resolved

    def validate_sql(self, raw_sql: str, schema_metadata: dict) -> str:
        """Validate raw SQL against policy. Returns normalized SQL string."""
        try:
            import sqlglot
        except ModuleNotFoundError as exc:
            raise BadRequestException("SQL validation requires 'sqlglot' to be installed.") from exc

        try:
            parsed = sqlglot.parse_one(raw_sql, dialect="postgres")
        except sqlglot.errors.ParseError as exc:
            raise BadRequestException(f"Invalid SQL syntax: {exc}")

        if parsed.key != "select":
            raise BadRequestException("Only SELECT statements are allowed")

        allowed_tables = self.resolve_allowed_tables(schema_metadata)
        self._validate_query_features(parsed)
        self._validate_tables(parsed, allowed_tables)
        self._validate_columns(parsed, allowed_tables)
        return parsed.sql(dialect="postgres")

    def _validate_query_features(self, parsed) -> None:
        import sqlglot

        if not self.allow_order_by and parsed.find(sqlglot.exp.Order):
            raise BadRequestException("ORDER BY is not allowed by policy")
        if not self.allow_subqueries and parsed.find(sqlglot.exp.Subquery):
            raise BadRequestException("Subqueries are not allowed by policy")

    def _validate_tables(self, parsed, allowed_tables: dict[str, set[str]]) -> None:
        import sqlglot

        allowed_table_names = set(allowed_tables.keys())
        for table_node in parsed.find_all(sqlglot.exp.Table):
            schema_name = (table_node.db or "").lower()
            table_name = (table_node.name or "").lower()
            qualified = f"{schema_name}.{table_name}" if schema_name else table_name

            if schema_name:
                if qualified not in allowed_table_names:
                    raise BadRequestException(
                        f"Table '{qualified}' is not allowed. Call lookup_schema to see available tables."
                    )
                continue

            candidates = [table for table in allowed_table_names if table.endswith(f".{table_name}")]
            if not candidates:
                raise BadRequestException(
                    f"Table '{qualified}' is not allowed. Call lookup_schema to see available tables."
                )
            if len(candidates) > 1:
                raise BadRequestException(
                    f"Table '{table_name}' is ambiguous. Use schema-qualified name. Call lookup_schema to check."
                )

            canonical = candidates[0]
            canonical_schema, canonical_table = canonical.split(".", maxsplit=1)
            table_node.set("db", sqlglot.exp.Identifier(this=canonical_schema))
            table_node.set("this", sqlglot.exp.Identifier(this=canonical_table))

    def _validate_columns(self, parsed, allowed_tables: dict[str, set[str]]) -> None:
        import sqlglot

        alias_map = self._build_sql_alias_map(parsed)
        select_aliases = self._collect_sql_select_aliases(parsed)
        referenced_tables = set(alias_map.values())

        allowed_for_referenced: set[str] = set()
        for table_key in referenced_tables:
            allowed_for_referenced.update(allowed_tables.get(table_key, set()))

        for col_node in parsed.find_all(sqlglot.exp.Column):
            col_name = col_node.name.lower()
            if col_name == "*":
                continue
            if col_name in select_aliases:
                continue

            table_ref = col_node.table
            if table_ref:
                qualified = alias_map.get(table_ref.lower(), table_ref.lower())
                allowed_cols = allowed_tables.get(qualified, set())
                if col_name not in allowed_cols:
                    raise BadRequestException(
                        f"Column '{col_name}' is not allowed for table '{qualified}'. "
                        f"Call lookup_schema to see available columns."
                    )
            elif col_name not in allowed_for_referenced:
                raise BadRequestException(
                    f"Column '{col_name}' is not recognized. "
                    f"Call lookup_schema to see available columns."
                )

    def _build_sql_alias_map(self, parsed) -> dict[str, str]:
        import sqlglot

        alias_map: dict[str, str] = {}
        for table_node in parsed.find_all(sqlglot.exp.Table):
            schema_name = (table_node.db or "").lower()
            table_name = (table_node.name or "").lower()
            qualified = f"{schema_name}.{table_name}" if schema_name else table_name

            if table_name:
                alias_map[table_name] = qualified
            if table_node.alias:
                alias_map[table_node.alias.lower()] = qualified
        return alias_map

    def _collect_sql_select_aliases(self, parsed) -> set[str]:
        import sqlglot

        aliases: set[str] = set()
        for select_node in parsed.find_all(sqlglot.exp.Select):
            for expression in select_node.expressions or []:
                if isinstance(expression, sqlglot.exp.Alias):
                    alias = expression.alias_or_name
                    if alias:
                        aliases.add(alias.lower())
        return aliases
