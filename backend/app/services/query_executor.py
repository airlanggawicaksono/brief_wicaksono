import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.business_policy.query_policy import QueryPolicy
from app.core.exceptions.base import BadRequestException
from app.dto.query import QueryPlan


class QueryExecutor:
    """Executes policy-sanitized query plans and read-only SQL against the database."""

    _ident_pattern = re.compile(r"^[a-z_][a-z0-9_]*$")

    def __init__(self, db: Session, query_policy: QueryPolicy):
        self.db = db
        self.query_policy = query_policy

    # Structured plan v2 execution
    def execute_plan_v2(
        self,
        plan: QueryPlan,
        schema_metadata: dict | None = None,
    ) -> tuple[list[dict], str]:
        allowed_tables = self.query_policy.resolve_allowed_tables(schema_metadata)
        sql = self._build_sql_from_plan(plan, allowed_tables=allowed_tables)
        validated_sql = self._validate_sql(sql, allowed_tables=allowed_tables)
        rows = self._execute_sql_with_guard(validated_sql)
        return rows, validated_sql

    # Raw SQL execution (read-only)
    def execute_raw_sql(self, raw_sql: str, schema_metadata: dict | None = None) -> list[dict]:
        allowed_tables = self.query_policy.resolve_allowed_tables(schema_metadata)
        validated_sql = self._validate_sql(raw_sql, allowed_tables=allowed_tables)
        return self._execute_sql_with_guard(validated_sql)

    def _execute_sql_with_guard(self, sql: str) -> list[dict]:
        self._apply_statement_timeout()
        result = self.db.execute(text(sql)).mappings()
        max_rows = max(1, self.query_policy.max_result_rows)
        rows = result.fetchmany(max_rows + 1)
        if len(rows) > max_rows:
            raise BadRequestException(f"Result set exceeds max_result_rows={max_rows}. Please narrow your query.")
        return [dict(row) for row in rows]

    def _apply_statement_timeout(self) -> None:
        timeout_ms = self.query_policy.statement_timeout_ms
        if timeout_ms <= 0:
            return
        try:
            self.db.execute(text("SET LOCAL statement_timeout = :timeout_ms"), {"timeout_ms": timeout_ms})
        except Exception:
            # Non-Postgres environments may not support this statement.
            pass

    def _validate_sql(self, raw_sql: str, allowed_tables: dict[str, set[str]]) -> str:
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

        self._validate_query_features(parsed)
        self._validate_tables(parsed, allowed_tables)
        self._validate_columns(parsed, allowed_tables)
        return parsed.sql(dialect="postgres")

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

    def _build_alias_map(self, parsed) -> dict[str, str]:
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

    def _collect_select_aliases(self, parsed) -> set[str]:
        import sqlglot

        aliases: set[str] = set()
        for select_node in parsed.find_all(sqlglot.exp.Select):
            for expression in select_node.expressions or []:
                if isinstance(expression, sqlglot.exp.Alias):
                    alias = expression.alias_or_name
                    if alias:
                        aliases.add(alias.lower())
        return aliases

    def _validate_query_features(self, parsed) -> None:
        import sqlglot

        if not self.query_policy.allow_order_by and parsed.find(sqlglot.exp.Order):
            raise BadRequestException("ORDER BY is not allowed by policy")
        if not self.query_policy.allow_subqueries and parsed.find(sqlglot.exp.Subquery):
            raise BadRequestException("Subqueries are not allowed by policy")

    def _validate_columns(self, parsed, allowed_tables: dict[str, set[str]]) -> None:
        import sqlglot

        alias_map = self._build_alias_map(parsed)
        select_aliases = self._collect_select_aliases(parsed)
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

    def _build_sql_from_plan(
        self,
        plan: QueryPlan,
        *,
        allowed_tables: dict[str, set[str]],
        depth: int = 0,
    ) -> str:
        if depth > 2:
            raise BadRequestException("Subquery depth exceeds execution limit")

        source_table = self._sanitize_table_ref(plan.source.table, allowed_tables)
        source_scope = self._sanitize_identifier(plan.source.alias) if plan.source.alias else source_table
        scope_map: dict[str, str] = {source_scope: source_table, source_table: source_table}

        select_sql: list[str] = []
        for item in plan.select:
            field_expr = self._compile_field_ref(item.field, scope_map, source_scope, allowed_tables)
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
            join_table = self._sanitize_table_ref(join.table, allowed_tables)
            join_scope = self._sanitize_identifier(join.alias) if join.alias else join_table

            temp_scope = {**scope_map, join_scope: join_table, join_table: join_table}
            left_expr = self._compile_field_ref(join.left_on, temp_scope, source_scope, allowed_tables)
            right_expr = self._compile_field_ref(join.right_on, temp_scope, join_scope, allowed_tables)

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
            sub_sql = self._build_sql_from_plan(subquery.plan, allowed_tables=allowed_tables, depth=depth + 1)

            temp_scope = {**scope_map, sub_alias: sub_alias}
            left_expr = self._compile_field_ref(subquery.join_on_left, temp_scope, source_scope, allowed_tables)
            right_expr = self._compile_field_ref(subquery.join_on_right, temp_scope, sub_alias, allowed_tables)

            join_kw = {"inner": "JOIN", "left": "LEFT JOIN", "right": "RIGHT JOIN"}[subquery.join_type]
            join_sql_parts.append(f"{join_kw} ({sub_sql}) AS {sub_alias} ON {left_expr} = {right_expr}")

        where_sql_parts: list[str] = []
        for filter_item in plan.filters:
            where_sql_parts.append(
                self._compile_filter(
                    filter_item.field, filter_item.op, filter_item.value, scope_map, source_scope, allowed_tables
                )
            )

        group_sql = ""
        if plan.group_by:
            group_items = [
                self._compile_field_ref(field, scope_map, source_scope, allowed_tables) for field in plan.group_by
            ]
            group_sql = f"GROUP BY {', '.join(group_items)}"

        order_sql = ""
        if plan.order_by:
            order_items = [
                f"{self._compile_field_ref(item.field, scope_map, source_scope, allowed_tables)} {item.direction.upper()}"
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
            table_ref = self._sanitize_table_ref(left, allowed_tables)
            return f"{table_ref}.{right}"

        if len(parts) == 3:
            schema = self._sanitize_identifier(parts[0])
            table_name = self._sanitize_identifier(parts[1])
            column = self._sanitize_identifier(parts[2])
            return f"{schema}.{table_name}.{column}"

        raise BadRequestException(f"Invalid field token '{token}'")

    def _compile_filter(
        self,
        field: str,
        op: str,
        value,
        scope_map: dict[str, str],
        default_scope: str,
        allowed_tables: dict[str, set[str]],
    ) -> str:
        left = self._compile_field_ref(field, scope_map, default_scope, allowed_tables)

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

    def _sanitize_identifier(self, token: str) -> str:
        normalized = token.strip().lower()
        if not self._ident_pattern.match(normalized):
            raise BadRequestException(f"Invalid identifier '{token}'")
        return normalized

    def _sanitize_table_ref(self, table_token: str, allowed_tables: dict[str, set[str]]) -> str:
        normalized = table_token.strip().lower()
        parts = normalized.split(".")

        if len(parts) == 1:
            token = self._sanitize_identifier(parts[0])
            if token in allowed_tables:
                return token
            candidates = [table for table in allowed_tables if table.endswith(f".{token}")]
            if len(candidates) == 1:
                return candidates[0]
            if len(candidates) > 1:
                raise BadRequestException(f"Table '{token}' is ambiguous. Use schema-qualified name")
            raise BadRequestException(f"Table '{token}' is not allowed")

        if len(parts) == 2:
            schema = self._sanitize_identifier(parts[0])
            table_name = self._sanitize_identifier(parts[1])
            value = f"{schema}.{table_name}"
            if value not in allowed_tables:
                raise BadRequestException(f"Table '{value}' is not allowed")
            return value

        raise BadRequestException(f"Invalid table reference '{table_token}'")

    def _literal(self, value) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        text_value = str(value).replace("'", "''")
        return f"'{text_value}'"
