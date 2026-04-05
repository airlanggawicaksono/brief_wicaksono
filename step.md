# Predict Endpoint Trace (Step by Step)

This traces the backend flow for:
- `POST /predict`
- source entry: `backend/app/api/v1/predict/__init__.py`

## Required I/O (General)

### Input (request)
- Endpoint: `POST /predict`
- Content-Type: `application/json`
- Body:
  - `text` (string, required): user message or question
- Optional session identity:
  - header `X-Session-Id`
  - or cookie `session_id`

### Output (response)
- Response type: `text/event-stream` (SSE)
- Streamed events (general):
  - progress/process updates
  - intent extraction
  - optional tool start/end events
  - assistant message
  - final structured result
  - done signal

### Final result shape (general)
- `input`: original user text
- `extraction`: detected intent + entities
- `mode`: execution mode (`direct` or tool/query path)
- `tool_results`: tool outputs (if tools were used)
- `process`: timeline of processing events
- `message`: final assistant reply text

### Optional history I/O
- Endpoint: `GET /predict/history?limit=<n>`
- Output: list of chat turns in simplified form:
  - `input` (user text)
  - `message` (assistant text)

## Dependency + Step I/O Contracts

### A) FastAPI dependency functions (`deps.py`)
- `get_session_id(request: Request) -> str`
  - Needs: incoming request object.
  - Reads: header `X-Session-Id`, then cookie `session_id`.
  - Returns: non-empty session id string (existing or generated UUID).

- `get_llm_provider() -> BaseChatModel`
  - Needs: env/config (`LLM_PROVIDER`, provider API key, provider model name).
  - Returns: configured chat model instance (OpenAI/Claude/Gemini).

- `get_query_tools(schema_service, query_policy, db) -> list`
  - Needs: `SchemaService`, `QueryPolicy`, SQLAlchemy `Session`.
  - Returns: tool list (currently `lookup_schema`, `query_table`).

- `get_intent_service(provider, intent_policy) -> IntentService`
  - Needs: LLM provider + intent policy.
  - Returns: service that converts text -> `PredictResponse` (intent/entities).

- `get_agent_service(provider, tools, tool_policy, query_policy) -> AgentService`
  - Needs: LLM provider, tool list, tool policy, query policy.
  - Returns: service that runs tool-calling loop and final answer generation.

- `get_predict_service(provider, intent_service, agent_service, intent_policy, chat_memory) -> PredictService`
  - Needs: all orchestration dependencies (intent, agent, direct responder, memory, presenter).
  - Returns: ready-to-run `PredictService`.

### B) Core orchestrator contract
- `PredictService.run_stream(text: str, session_id: str) -> Generator[str]`
  - Needs:
    - `text`: non-empty user input (from request body)
    - `session_id`: stable conversation id
    - Redis for chat history and cache
    - LLM provider + optional DB tool path dependencies
  - Produces:
    - SSE chunks as strings (`event: ...\ndata: ...\n\n`)
    - terminal `done` event
  - Final semantic output:
    - one `PredictResult` (sent as SSE `result`, or cached result via `cached`)

### C) Step contracts (`steps.py`)
- `IntentStep.run(ctx: RequestContext) -> StepResult[PredictResponse]`
  - Needs:
    - `ctx.text`
    - working `IntentService`
  - Returns:
    - `ok=True`, `output=PredictResponse(intent, entities)` on success
    - `ok=False`, `error={message: ...}` on failure
    - events list including `received_input` and `intent_detected` (or `failed`)

- `AgentStep.run(extraction: PredictResponse, ctx: RequestContext) -> StepResult[dict]`
  - Needs:
    - `extraction.intent` (usually `data_query`)
    - `extraction.entities` (optional dict)
    - `ctx.text`, `ctx.history`
    - working `AgentService` + tools
  - Returns:
    - `ok=True`
    - `output` shape:
      - `tool_results: list[ToolExecution]` (successful tool outputs)
      - `message: str` (final assistant text)
    - events: `agent_started`, optional `tool_start/tool_end`, final `message`

- `DirectResponseStep.run(extraction: PredictResponse, ctx: RequestContext) -> StepResult[str]`
  - Needs:
    - `extraction.intent` (`general` or `clarification`)
    - `ctx.text`, `ctx.history`
    - direct LLM provider
  - Returns:
    - `ok=True`
    - `output`: assistant response string
    - events: `direct_response`, final `message`

### D) Agent loop contract (`services/agent`)
- `AgentService.execute(text, history=None, intent="data_query", entities=None) -> Generator[ToolExecution | str]`
  - Needs:
    - user text + optional chat history
    - intent (decides tool allowlist)
    - tool executor and bound tool-capable LLM
  - Yields:
    - `ToolExecution(..., data=None)` before running each tool
    - `ToolExecution(..., data=<tool result>)` after tool returns
    - final `str` answer when no more tool calls

- `ToolExecutor.invoke(tool_name: str, tool_args: dict) -> object`
  - Needs:
    - tool exists in registry
    - valid args for selected tool
  - Returns:
    - tool output object
    - or normalized error object (`tool_not_found`, validation, runtime)

### E) Tool contracts (`services/tools`)
- `lookup_schema(table_name: str | None = None, detail_level: str = "summary") -> dict`
  - Needs: SQLAlchemy ORM metadata registry.
  - Returns: available schemas/tables/columns/relationships (or table-not-found error).

- `query_table(sql: str) -> dict`
  - Needs:
    - SQL string (SELECT only)
    - DB session
    - schema metadata
    - query policy validation
  - Returns on success:
    - `row_count`, `rows`, `executed_sql`
  - Returns on failure:
    - `{"error": {"code": "...", "message": "..."}}`

### F) Infra requirements (runtime dependencies)
- LLM provider credentials and model config must be set.
- Redis must be reachable (chat memory + response cache).
- Postgres must be reachable for `query_table` tool path.
- Python packages for selected provider/tooling must be installed (LangChain integrations, Redis client, SQL validator).

## Detailed: How `entities` are handled for `data_query`

### 1) Where entities come from
- `IntentService.detect(...)` asks the intent model to return:
  - `intent`
  - `entities` (freeform key-value pairs)
- Prompt rule: for non-data intents, entities should be `null`; for `data_query`, entities may be a dict.

### 2) Normalization and pass-through
- After detection, intent is normalized by policy (`data_query`, `general`, `clarification`).
- `entities` are not normalized into a strict schema; they remain freeform.
- In `AgentStep.run(...)`, backend safely applies:
  - if `entities` is a dict -> keep it
  - otherwise -> set to `None`

### 3) How entities influence behavior
- Entities are passed to `AgentService.execute(..., entities=...)`.
- `MessageBuilder` injects them into the LLM context as a system message:
  - `Extracted user intent context: key=value, ...`
- This helps the LLM plan better tool calls and SQL (soft steering).

### 4) What entities do NOT do
- Entities are not converted by backend into deterministic SQL filters.
- Entities are not enforced by policy as mandatory constraints.
- Entities do not bypass SQL safety checks.
- Actual execution still depends on:
  - LLM tool-calling decisions
  - `query_table` validation (`SELECT` only, allowed tables/columns, row limits, etc.)

### 5) Practical effect
- If entities are useful and specific (brand/date/metric/etc.), query planning often improves.
- If entities are missing, noisy, or empty, flow still works; the LLM falls back to user text + schema/tool feedback loop.
- Final guardrails remain in query policy, not entities.

### 6) Visibility in output/UI
- Entities are visible in SSE `extraction` event payload.
- Entities are included in final `result.extraction`.
- Frontend may display entities in the intent step for transparency/debugging.

## 1) HTTP request enters route
1. FastAPI receives `POST /predict`.
2. Handler `predict(...)` is called in `backend/app/api/v1/predict/__init__.py`.
3. Request body is parsed as `PredictRequest` (`text: str`).

## 2) Dependencies are resolved
4. `get_session_id(...)` runs:
   - first tries header `X-Session-Id`
   - then cookie `session_id`
   - if none, generates `uuid4()`
5. `get_predict_service(...)` builds `PredictService` with:
   - `IntentStep`
   - `AgentStep`
   - `DirectResponseStep`
   - `RedisChatMemory`
   - `SsePresenter`
6. LLM provider is created via `create_llm_provider()` (OpenAI/Claude/Gemini from env) and reused with `lru_cache`.

## 3) Route returns a streaming response
7. Route wraps `service.run_stream(body.text, session_id=...)` in `StreamingResponse`.
8. Response headers include:
   - `Content-Type: text/event-stream`
   - `Cache-Control: no-cache`
   - `X-Accel-Buffering: no`
   - `X-Session-Id: <session_id>`
9. Route also sets cookie `session_id=<session_id>`.

## 4) PredictService starts orchestration
10. `run_stream(...)` loads recent chat history from Redis (`limit=20`).
11. It builds `RequestContext(session_id, text, history)`.
12. It checks Redis cache with key based on `(session_id + normalized text)`.

## 5) Cache short-circuit (fast path)
13. If cached result exists and validates:
   - emit SSE event `cached`
   - emit SSE event `done`
   - stop.

## 6) Normal path: detect intent first
14. `IntentStep.run(ctx)` emits process event: `received_input`.
15. `IntentService.detect(text)` calls structured LLM output (`PredictResponse`).
16. Intent is normalized by policy:
   - valid: `data_query`, `general`, `clarification`
   - unknown -> `clarification`
17. `IntentStep` emits SSE extraction event (`event: extraction`) with detected intent/entities.

## 7) Branching by intent
18. If intent is `data_query` -> go to Agent path.
19. Otherwise (`general` or `clarification`) -> go to Direct response path.

## 8) Agent path (`data_query`)
20. `AgentStep.run(...)` emits `agent_started`.
21. `AgentService.execute(...)` prepares conversation:
   - system agent prompt
   - dynamic tool context (available tools + query constraints)
   - language hint
   - optional extracted entities
   - prior chat history
   - current user text
22. Tool policy allowlist for `data_query` is:
   - `lookup_schema`
   - `query_table`
23. LLM may call tools in a loop (max rounds from policy, default 25):
   - before execution emit `tool_start`
   - run tool via `ToolExecutor`
   - emit `tool_end` with compact data (or error shape)
   - append tool output back into conversation as `ToolMessage`
24. If `query_table` fails with schema-related error, a system nudge is added telling model to call `lookup_schema`.
25. When LLM stops tool-calling, final text message is emitted as SSE `message`.

## 9) Direct response path (non-data intent)
26. `DirectResponseStep.run(...)` emits `direct_response`.
27. It chooses prompt:
   - `CLARIFICATION_PROMPT` for `clarification`
   - `GENERAL_PROMPT` for `general`
28. It calls LLM with history + current text.
29. Emits final SSE `message`.

## 10) Final assembly and persistence
30. Service builds `PredictResult` containing:
   - input
   - extraction
   - mode (`query_table` if tool results exist, else `direct`)
   - tool results
   - full process events
   - final message
31. Result is cached in Redis (24h TTL).
32. Turn is appended to Redis chat memory as:
   - user message
   - assistant message
33. Service emits SSE `result`.
34. Service emits SSE `done`.

## 11) SSE event order you normally see
35. Typical order:
   - `process` (received_input)
   - `extraction`
   - `process` (agent_started or direct_response)
   - zero or more `tool_start` / `tool_end` (data_query branch only)
   - `message`
   - `result`
   - `done`

## 12) History endpoint
36. `GET /predict/history?limit=20` reads Redis chat messages for the same session id.
37. It pairs user/assistant turns and returns:
   - `[{ "input": "...", "message": "..." }, ...]`

## Key files in this trace
- `backend/app/api/v1/predict/__init__.py`
- `backend/app/api/v1/predict/deps.py`
- `backend/app/services/predict/__init__.py`
- `backend/app/services/predict/steps.py`
- `backend/app/services/predict/presenter.py`
- `backend/app/services/intent/__init__.py`
- `backend/app/services/agent/__init__.py`
- `backend/app/services/tools/__init__.py`
- `backend/app/services/tools/schema.py`
- `backend/app/services/tools/query.py`
- `backend/app/policy/intent.py`
- `backend/app/policy/tool.py`
- `backend/app/repository/chat_memory.py`
- `backend/app/core/infra/cache.py`
