# System Design Write-up

## Overview

A natural language interface for marketing analytics. Users type plain text; the system detects intent, queries a relational database if needed, and streams a human-readable response back in real time via SSE.

---

## System Design

The backend is a FastAPI application structured in clean layers: API, Services, Policy, Repository. Each layer has a single responsibility and no upward dependencies. Tools live under Services as executable units consumed by the agent.

The core flow has two branches. **Intent detection** runs first on every request, returning `intent` and `entities` as a typed Pydantic model. Intent resolves to one of three values: `data_query`, `general`, or `clarification`. Unknown or malformed outputs are normalised to `clarification` by the policy layer. If the intent is `data_query`, the request enters the agent path. Otherwise a direct LLM response is generated using a prompt selected by intent.

---

## Agent Loop

The agent is a self-directing tool loop built on LangChain's tool-calling interface. On each iteration the LLM receives the full conversation history including all prior tool results, then returns either tool calls (continue) or a plain text response (done). Tools execute, results are appended as `ToolMessage`, and the LLM re-invokes. The loop exits when the LLM stops requesting tools.

No Python heuristics determine what "sufficient" means; that judgement lives entirely in the LLM via prompt instructions. This makes the loop tool-agnostic: adding new tools requires no changes to the loop logic.

---

## Context Injection

Before every agent invocation, `MessageBuilder` assembles the full conversation context. Beyond the base system prompt, two layers are injected at runtime:

**Tool context** is built from live tool objects and the active query policy:

```
## Available tools
- lookup_schema: Inspect schema metadata before planning a query.
  Always call this before query_table to see available tables, columns, and relationships.
- query_table: Execute a read-only SQL SELECT query against the database.

## Query constraints
- max_result_rows: 100
- allow_order_by: True
- allow_subqueries: False
- write_operations: disabled (SELECT only)
```

If a new tool is added or a policy value changes, this context updates automatically with no prompt edits needed.

**Entity context** is injected when the intent step extracted structured entities. For example, for "show Wardah campaigns this month":

```
Extracted entities from user input: {"brand": "Wardah", "date_range": "current month"}
```

This steers the agent toward more precise queries without hardcoding any filtering logic in Python. SQL safety is still enforced by the policy layer regardless.

---

## Structure

```
backend/
  app/
    api/          - routes and dependency injection
    services/     - business logic (predict, agent, intent, tools)
    policy/       - query validation, intent normalisation, tool allowlist
    repository/   - Redis chat memory
    prompts/      - LLM system prompts
    core/         - enums, exceptions, provider factory, infra utilities
```

The LLM provider is abstracted behind a factory driven by `LLM_PROVIDER` in env config. Swapping providers requires a single env change, no code changes. The frontend receives SSE via axios `onDownloadProgress` rather than native `EventSource`, which only supports GET. Each event type maps to a typed callback, keeping transport logic isolated from UI components.

---

## Handling of AI Output

**Structured extraction** uses LangChain structured output so intent detection always returns a typed Pydantic model. Unrecognised intent strings are normalised to `clarification` by policy.

**SQL validation** runs every generated query through `sqlglot` before execution. Non-SELECT statements, disallowed tables, and results exceeding the row limit are rejected before reaching the database.

**Self-evaluation in the agent** instructs the LLM to assess each tool result itself: is the data human-readable, does it fully answer the question? The LLM decides the next action rather than Python detecting specific failure cases. This scales to any number of tools without brittle case-by-case handling in code.

---

## Trade-offs

**SSE over WebSockets** is sufficient for one-way streaming and avoids bidirectional complexity the current use case does not need.

**Self-directing loop over LangGraph** keeps the dependency surface small and control flow explicit. The trade-off is that complex multi-step pipelines will require careful prompt engineering to sequence correctly. LangGraph would handle branching and retry logic more formally.

**Extensibility through interface contracts** means adding a tool requires no changes to the loop, prompt, or routing logic. A tool is defined once with a typed function signature and a docstring, and that single definition drives multiple responsibilities simultaneously:

```python
@tool
def query_table(sql: str) -> dict:
    """Execute a read-only SQL SELECT query against the database.

    Call lookup_schema first to discover available tables and columns.
    """
    ...
```

From this one definition:
- The type annotation `sql: str` becomes the JSON Schema the LLM API enforces on `tool_calls[].args` at inference time
- The docstring becomes the description the LLM reads to decide when and how to call the tool
- Both the name and description are picked up by `build_tool_context` and injected into every agent conversation automatically

Nothing is declared twice. The contract that enforces correct argument types at runtime is the same contract the LLM uses to understand the tool at inference time. This tight coupling means the system stays consistent by construction: there is no separate metadata file, no prompt snippet, and no registration step to keep in sync when a tool changes.

**Single LLM call for intent** adds latency but keeps classification clean and independently testable rather than embedding it inside the agent prompt.

**ORM-based schema introspection** means schema changes are automatically visible to the agent. Tables not mapped in the ORM are invisible, which is a deliberate constraint that prevents the agent from querying unintended tables.
