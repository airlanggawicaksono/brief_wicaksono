from dataclasses import dataclass, field

from app.core.exceptions.base import BadRequestException
from app.dto.query import QueryPlan


@dataclass(frozen=True)
class QueryPolicy:
    """Business policy for safe, metadata-driven read-only querying."""

    allowed_tables: dict[str, set[str]] = field(
        default_factory=lambda: {
            "product.products": {"id", "name", "category", "price", "brand"},
            "product.audiences": {"id", "name", "min_age", "max_age", "preferences"},
            "marketing.campaigns": {"id", "name", "product_id", "audience_id", "budget"},
            "marketing.performance": {"id", "campaign_id", "impressions", "clicks", "conversions"},
        }
    )
    allowed_operators: set[str] = field(default_factory=lambda: {"eq", "ilike", "lt", "lte", "gt", "gte", "in"})
    allowed_join_edges: set[tuple[str, str]] = field(
        default_factory=lambda: {
            ("marketing.campaigns", "product.products"),
            ("marketing.campaigns", "product.audiences"),
            ("marketing.performance", "marketing.campaigns"),
        }
    )

    allow_order_by: bool = True
    allow_subqueries: bool = True

    statement_timeout_ms: int = 8_000
    max_result_rows: int = 2_000

    def resolve_allowed_tables(self, schema_metadata: dict | None = None) -> dict[str, set[str]]:
        """Derive allowlisted tables/columns from schema metadata when available."""
        if not isinstance(schema_metadata, dict):
            return dict(self.allowed_tables)

        tables_payload = schema_metadata.get("tables")
        if not isinstance(tables_payload, dict):
            return dict(self.allowed_tables)

        resolved: dict[str, set[str]] = {}
        for table_key, table_meta in tables_payload.items():
            if not isinstance(table_key, str) or not isinstance(table_meta, dict):
                continue

            raw_names = table_meta.get("column_names")
            if not isinstance(raw_names, list):
                raw_columns = table_meta.get("columns")
                if isinstance(raw_columns, list):
                    names_from_columns: list[str] = []
                    for col in raw_columns:
                        if isinstance(col, dict) and isinstance(col.get("name"), str):
                            names_from_columns.append(col["name"])
                    raw_names = names_from_columns

            if not isinstance(raw_names, list):
                continue

            normalized_names = {name.strip().lower() for name in raw_names if isinstance(name, str) and name.strip()}
            if normalized_names:
                resolved[table_key.strip().lower()] = normalized_names

        return resolved or dict(self.allowed_tables)

    def resolve_allowed_join_edges(
        self,
        schema_metadata: dict | None = None,
        allowed_tables: dict[str, set[str]] | None = None,
    ) -> set[tuple[str, str]]:
        """Derive allowed join edges from metadata relationships plus static policy edges."""
        tables = allowed_tables or self.resolve_allowed_tables(schema_metadata)
        edges: set[tuple[str, str]] = set()

        for left, right in self.allowed_join_edges:
            if left in tables and right in tables:
                edges.add((left, right))

        if not isinstance(schema_metadata, dict):
            return edges or set(self.allowed_join_edges)

        relationships = schema_metadata.get("relationships")
        if not isinstance(relationships, list):
            return edges or set(self.allowed_join_edges)

        for rel in relationships:
            source_table, _ = self._parse_column_ref(self._extract_ref(rel, "source"))
            target_table, _ = self._parse_column_ref(self._extract_ref(rel, "target"))
            if not source_table or not target_table:
                continue
            if source_table in tables and target_table in tables:
                edges.add((source_table, target_table))

        return edges or set(self.allowed_join_edges)

    def validate_plan_v2(
        self,
        plan: QueryPlan,
        schema_metadata: dict | None = None,
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
