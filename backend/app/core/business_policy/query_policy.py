import re
from dataclasses import dataclass, field

from app.core.exceptions.base import BadRequestException
from app.dto.query import QueryPlan


_IDENT_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass(frozen=True)
class QueryPolicy:
    """Business policy for safe, metadata-driven read-only querying."""

    allowed_operators: set[str] = field(default_factory=lambda: {"eq", "ilike", "lt", "lte", "gt", "gte", "in"})

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

    def resolve_allowed_join_edges(
        self,
        schema_metadata: dict,
        allowed_tables: dict[str, set[str]] | None = None,
    ) -> set[tuple[str, str]]:
        """Derive allowed join edges from FK relationships in schema metadata."""
        tables = allowed_tables or self.resolve_allowed_tables(schema_metadata)
        edges: set[tuple[str, str]] = set()

        relationships = schema_metadata.get("relationships")
        if not isinstance(relationships, list):
            return edges

        for rel in relationships:
            source_table, _ = self._parse_column_ref(self._extract_ref(rel, "source"))
            target_table, _ = self._parse_column_ref(self._extract_ref(rel, "target"))
            if not source_table or not target_table:
                continue
            if source_table in tables and target_table in tables:
                edges.add((source_table, target_table))

        return edges

    def validate_plan_v2(
        self,
        plan: QueryPlan,
        schema_metadata: dict,
        *,
        depth: int = 0,
    ) -> QueryPlan:
        if depth > 2:
            raise BadRequestException("Subquery depth exceeds policy limit")

        allowed_tables = self.resolve_allowed_tables(schema_metadata)
        allowed_join_edges = self.resolve_allowed_join_edges(schema_metadata, allowed_tables=allowed_tables)

        source_table = self._canonical_table(plan.source.table, allowed_tables)
        alias_map: dict[str, str] = {source_table: source_table}
        if plan.source.alias:
            alias_map[plan.source.alias] = source_table

        for join in plan.joins:
            right_table = self._canonical_table(join.table, allowed_tables)

            left_table, left_col = self._resolve_field(join.left_on, alias_map, source_table, allowed_tables)
            right_scope = {**alias_map, right_table: right_table}
            if join.alias:
                right_scope[join.alias] = right_table
            right_ref_table, right_col = self._resolve_field(join.right_on, right_scope, right_table, allowed_tables)

            if right_ref_table != right_table:
                raise BadRequestException(
                    f"Join right side must reference joined table '{right_table}'. Received '{right_ref_table}'."
                )

            self._ensure_column_allowed(left_table, left_col, allowed_tables)
            self._ensure_column_allowed(right_table, right_col, allowed_tables)

            valid_edge = any(
                (left_table, right_table) == edge or (right_table, left_table) == edge for edge in allowed_join_edges
            )
            if not valid_edge:
                raise BadRequestException(f"Join path '{left_table} -> {right_table}' is not allowed")

            alias_map[right_table] = right_table
            if join.alias:
                alias_map[join.alias] = right_table

        for select_item in plan.select:
            if select_item.field == "*":
                continue
            table_name, column_name = self._resolve_field(select_item.field, alias_map, source_table, allowed_tables)
            self._ensure_column_allowed(table_name, column_name, allowed_tables)

        projected_names = self._collect_projected_names(plan)

        for group_field in plan.group_by:
            normalized_group = group_field.strip().lower()
            if "." not in normalized_group and normalized_group in projected_names:
                continue
            table_name, column_name = self._resolve_field(group_field, alias_map, source_table, allowed_tables)
            self._ensure_column_allowed(table_name, column_name, allowed_tables)

        if plan.order_by and not self.allow_order_by:
            raise BadRequestException("ORDER BY is not allowed by policy")
        for order_item in plan.order_by:
            normalized_order = order_item.field.strip().lower()
            if "." not in normalized_order and normalized_order in projected_names:
                continue
            table_name, column_name = self._resolve_field(order_item.field, alias_map, source_table, allowed_tables)
            self._ensure_column_allowed(table_name, column_name, allowed_tables)

        for filter_item in plan.filters:
            if filter_item.op not in self.allowed_operators:
                raise BadRequestException(f"Operator '{filter_item.op}' is not allowed")
            table_name, column_name = self._resolve_field(filter_item.field, alias_map, source_table, allowed_tables)
            self._ensure_column_allowed(table_name, column_name, allowed_tables)

        if plan.subqueries and not self.allow_subqueries:
            raise BadRequestException("Subqueries are not allowed by policy")

        for subquery in plan.subqueries:
            self.validate_plan_v2(subquery.plan, schema_metadata=schema_metadata, depth=depth + 1)
            sub_alias = subquery.alias.strip().lower()

            left_table, left_col = self._resolve_field(
                subquery.join_on_left,
                {**alias_map, sub_alias: sub_alias},
                source_table,
                allowed_tables,
            )
            self._ensure_column_allowed(left_table, left_col, allowed_tables)

            right_tokens = subquery.join_on_right.split(".")
            if len(right_tokens) != 2 or right_tokens[0].strip().lower() != sub_alias:
                raise BadRequestException(f"Subquery join_on_right must reference '{sub_alias}.<column>'")

            subquery_field = right_tokens[1].strip().lower()
            projected_fields = self._collect_projected_names(subquery.plan)
            if "*" not in projected_fields and subquery_field not in projected_fields:
                raise BadRequestException(
                    f"Subquery alias field '{sub_alias}.{subquery_field}' is not projected by the subquery plan"
                )

        normalized_source = plan.source.model_copy(update={"table": source_table})
        return plan.model_copy(update={"source": normalized_source})

    def _extract_ref(self, rel: object, key: str) -> str | None:
        if isinstance(rel, dict):
            value = rel.get(key)
            if isinstance(value, str):
                return value.strip().lower()
            if all(isinstance(rel.get(part), str) for part in (f"{key}_schema", f"{key}_table", f"{key}_column")):
                return (f"{rel[f'{key}_schema']}.{rel[f'{key}_table']}.{rel[f'{key}_column']}").strip().lower()
        return None

    def _parse_column_ref(self, ref: str | None) -> tuple[str | None, str | None]:
        if not ref:
            return None, None
        tokens = [part.strip().lower() for part in ref.split(".") if part.strip()]
        if len(tokens) < 3:
            return None, None
        table = f"{tokens[0]}.{tokens[1]}"
        return table, tokens[2]

    def _collect_projected_names(self, plan: QueryPlan) -> set[str]:
        projected: set[str] = set()
        for item in plan.select:
            if item.field == "*":
                projected.add("*")
                continue
            if item.alias:
                projected.add(item.alias.strip().lower())
                continue
            projected.add(item.field.split(".")[-1].strip().lower())
        return projected

    def _canonical_table(self, token: str, allowed_tables: dict[str, set[str]]) -> str:
        normalized = token.strip().lower()
        if normalized in allowed_tables:
            return normalized

        candidates = [table for table in allowed_tables if table.endswith(f".{normalized}")]
        if not candidates:
            raise BadRequestException(f"Table '{token}' is not allowed")
        if len(candidates) > 1:
            raise BadRequestException(f"Table '{token}' is ambiguous. Use schema-qualified name")
        return candidates[0]

    def _resolve_field(
        self,
        field_token: str,
        alias_map: dict[str, str],
        default_table: str,
        allowed_tables: dict[str, set[str]],
    ) -> tuple[str, str]:
        token = field_token.strip().lower()
        if token == "*":
            return default_table, token

        parts = token.split(".")
        if len(parts) == 1:
            return default_table, parts[0]

        if len(parts) == 2:
            left, column = parts
            table = alias_map.get(left)
            if table:
                return table, column
            return self._canonical_table(left, allowed_tables), column

        if len(parts) == 3:
            schema, table_name, column = parts
            table = f"{schema}.{table_name}"
            return self._canonical_table(table, allowed_tables), column

        raise BadRequestException(f"Invalid field token '{field_token}'")

    def _ensure_column_allowed(self, table: str, column: str, allowed_tables: dict[str, set[str]]) -> None:
        if column == "*":
            return
        if table not in allowed_tables:
            raise BadRequestException(f"Table '{table}' is not allowed")
        if column not in allowed_tables[table]:
            raise BadRequestException(f"Column '{column}' is not allowed for table '{table}'")

    # --- Raw SQL validation (sqlglot-based) ---

    def validate_sql(self, raw_sql: str, schema_metadata: dict) -> str:
        """Validate raw SQL against policy. Returns normalized SQL string."""
        try:
            import sqlglot
        except ModuleNotFoundError as exc:
            raise BadRequestException("Raw SQL validation requires 'sqlglot' to be installed.") from exc

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
                        f"Table '{qualified}' is not allowed. Allowed: {sorted(allowed_table_names)}"
                    )
                continue

            candidates = [table for table in allowed_table_names if table.endswith(f".{table_name}")]
            if not candidates:
                raise BadRequestException(f"Table '{qualified}' is not allowed. Allowed: {sorted(allowed_table_names)}")
            if len(candidates) > 1:
                raise BadRequestException(f"Table '{table_name}' is ambiguous. Use schema-qualified name.")

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
                    raise BadRequestException(f"Column '{col_name}' is not allowed for table '{qualified}'")
            elif col_name not in allowed_for_referenced:
                raise BadRequestException(
                    f"Column '{col_name}' is not in the allowed column set for the referenced tables"
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

    # --- SQL building from QueryPlan ---

    def build_sql(
        self,
        plan: QueryPlan,
        *,
        allowed_tables: dict[str, set[str]],
        depth: int = 0,
    ) -> str:
        """Build a SQL string from a validated QueryPlan."""
        if depth > 2:
            raise BadRequestException("Subquery depth exceeds execution limit")

        tables = allowed_tables

        source_table = self._canonical_table(plan.source.table, tables)
        source_scope = self._sanitize_identifier(plan.source.alias) if plan.source.alias else source_table
        scope_map: dict[str, str] = {source_scope: source_table, source_table: source_table}

        select_sql: list[str] = []
        for item in plan.select:
            field_expr = self._compile_field_ref(item.field, scope_map, source_scope, tables)
            expression = field_expr
            if item.aggregate:
                distinct = "DISTINCT " if item.distinct else ""
                expression = f"{item.aggregate.upper()}({distinct}{field_expr})"
            if item.alias:
                expression = f"{expression} AS {self._sanitize_identifier(item.alias)}"
            select_sql.append(expression)
        if not select_sql:
            select_sql = ["*"]

        from_sql = f"FROM {source_table}"
        if plan.source.alias:
            from_sql += f" AS {self._sanitize_identifier(plan.source.alias)}"

        join_sql_parts: list[str] = []
        for join in plan.joins:
            join_table = self._canonical_table(join.table, tables)
            join_scope = self._sanitize_identifier(join.alias) if join.alias else join_table

            temp_scope = {**scope_map, join_scope: join_table, join_table: join_table}
            left_expr = self._compile_field_ref(join.left_on, temp_scope, source_scope, tables)
            right_expr = self._compile_field_ref(join.right_on, temp_scope, join_scope, tables)

            scope_map[join_scope] = join_table
            scope_map[join_table] = join_table

            join_kw = {"inner": "JOIN", "left": "LEFT JOIN", "right": "RIGHT JOIN"}[join.join_type]
            join_part = f"{join_kw} {join_table}"
            if join.alias:
                join_part += f" AS {self._sanitize_identifier(join.alias)}"
            join_part += f" ON {left_expr} = {right_expr}"
            join_sql_parts.append(join_part)

        for subquery in plan.subqueries:
            sub_alias = self._sanitize_identifier(subquery.alias)
            sub_sql = self.build_sql(subquery.plan, allowed_tables=tables, depth=depth + 1)

            temp_scope = {**scope_map, sub_alias: sub_alias}
            left_expr = self._compile_field_ref(subquery.join_on_left, temp_scope, source_scope, tables)
            right_expr = self._compile_field_ref(subquery.join_on_right, temp_scope, sub_alias, tables)

            join_kw = {"inner": "JOIN", "left": "LEFT JOIN", "right": "RIGHT JOIN"}[subquery.join_type]
            join_sql_parts.append(f"{join_kw} ({sub_sql}) AS {sub_alias} ON {left_expr} = {right_expr}")

        where_sql_parts: list[str] = []
        for filter_item in plan.filters:
            where_sql_parts.append(
                self._compile_filter(filter_item.field, filter_item.op, filter_item.value, scope_map, source_scope, tables)
            )

        group_sql = ""
        if plan.group_by:
            group_items = [self._compile_field_ref(f, scope_map, source_scope, tables) for f in plan.group_by]
            group_sql = f"GROUP BY {', '.join(group_items)}"

        order_sql = ""
        if plan.order_by:
            order_items = [
                f"{self._compile_field_ref(item.field, scope_map, source_scope, tables)} {item.direction.upper()}"
                for item in plan.order_by
            ]
            order_sql = f"ORDER BY {', '.join(order_items)}"

        limit_sql = f"LIMIT {plan.limit}" if plan.limit is not None else ""
        offset_sql = f"OFFSET {plan.offset}" if plan.offset is not None else ""

        segments = [f"SELECT {', '.join(select_sql)}", from_sql, *join_sql_parts]
        if where_sql_parts:
            segments.append(f"WHERE {' AND '.join(where_sql_parts)}")
        if group_sql:
            segments.append(group_sql)
        if order_sql:
            segments.append(order_sql)
        if limit_sql:
            segments.append(limit_sql)
        if offset_sql:
            segments.append(offset_sql)

        return "\n".join(segments)

    def _sanitize_identifier(self, token: str) -> str:
        normalized = token.strip().lower()
        if not _IDENT_PATTERN.match(normalized):
            raise BadRequestException(f"Invalid identifier '{token}'")
        return normalized

    def _compile_field_ref(
        self,
        token: str,
        scope_map: dict[str, str],
        default_scope: str,
        allowed_tables: dict[str, set[str]],
    ) -> str:
        value = token.strip().lower()
        if value == "*":
            return "*"

        parts = value.split(".")
        if len(parts) == 1:
            return f"{default_scope}.{self._sanitize_identifier(parts[0])}"

        if len(parts) == 2:
            left = self._sanitize_identifier(parts[0])
            right = self._sanitize_identifier(parts[1])
            if left in scope_map:
                return f"{left}.{right}"
            table_ref = self._canonical_table(left, allowed_tables)
            return f"{table_ref}.{right}"

        if len(parts) == 3:
            schema = self._sanitize_identifier(parts[0])
            table_name = self._sanitize_identifier(parts[1])
            column = self._sanitize_identifier(parts[2])
            return f"{schema}.{table_name}.{column}"

        raise BadRequestException(f"Invalid field token '{token}'")

    def _compile_filter(
        self,
        field_token: str,
        op: str,
        value,
        scope_map: dict[str, str],
        default_scope: str,
        allowed_tables: dict[str, set[str]],
    ) -> str:
        left = self._compile_field_ref(field_token, scope_map, default_scope, allowed_tables)

        if op == "eq":
            return f"{left} = {self._literal(value)}"
        if op == "ilike":
            return f"{left} ILIKE {self._literal(f'%{value}%')}"
        if op == "lt":
            return f"{left} < {self._literal(value)}"
        if op == "lte":
            return f"{left} <= {self._literal(value)}"
        if op == "gt":
            return f"{left} > {self._literal(value)}"
        if op == "gte":
            return f"{left} >= {self._literal(value)}"
        if op == "in":
            values = value if isinstance(value, list) else [value]
            if not values:
                raise BadRequestException("IN filter requires at least one value")
            rendered = ", ".join(self._literal(item) for item in values)
            return f"{left} IN ({rendered})"

        raise BadRequestException(f"Unsupported operator '{op}'")

    def _literal(self, value) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        text_value = str(value).replace("'", "''")
        return f"'{text_value}'"
