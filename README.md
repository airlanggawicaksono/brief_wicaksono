# WPP AI Assistant

AI-powered natural language interface for marketing analytics. Converts user input into structured intent + entities, then uses a self-directing agent loop to query a PostgreSQL database and return human-readable results.

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, LangChain, SQLAlchemy |
| Frontend | Next.js 15, React 19, Tailwind |
| Database | PostgreSQL 16 |
| Cache / Memory | Redis (chat history + response cache) |
| LLM | OpenAI (default), Anthropic, Google Gemini |

---

## Prerequisites

- [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) — Windows requires [WSL 2](https://learn.microsoft.com/en-us/windows/wsl/install) enabled first
- An OpenAI API key (or Anthropic / Google — see [LLM providers](#llm-providers))
- `make` — Linux/macOS: built-in. Windows: install via [Chocolatey](https://chocolatey.org/install) → `choco install make`

---

## Setup

### 1. Copy and fill the env file

```bash
cp .env.example .env
```

Open `.env` and set your API key:

```env
OPENAI_API_KEY=sk-...
```

Everything else works with the defaults. The database is pre-seeded with sample products, audiences, campaigns, and performance data on first startup — no manual data loading needed.

### 2. Start all services

**Linux / macOS:**
```bash
make dev-up
```

**Windows — without make:**
```bash
docker compose --env-file .env up -d
```

### 3. Open the app

| Service | URL |
|---|---|
| Frontend | http://localhost:3071 |
| Backend API docs | http://localhost:8037/docs |

---

## Stopping

**With make:**
```bash
make dev-down
```

**Without make:**
```bash
docker compose --env-file .env down
```

**Full reset — removes all volumes and caches:**
```bash
# with make
make clean

# without make (macOS)
docker compose --env-file .env down -v --remove-orphans
docker builder prune -af
docker image prune -af
```

---

## LLM Providers

Set `LLM_PROVIDER` in `.env` to switch providers:

**OpenAI (default)**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini-2025-04-14
```

**Anthropic**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

**Google Gemini**
```env
LLM_PROVIDER=google
GOOGLE_API_KEY=...
GOOGLE_MODEL=gemini-2.0-flash
```

---

## How it works

```
User input
   ↓
Intent detection      → structured output: intent + entities
   ↓
Branch decision
   ├── data_query      → Agent loop: LLM selects tools, executes SQL,
   │                     self-evaluates result quality, repeats until satisfied
   └── general /       → Direct LLM response (no tools)
       clarification
   ↓
Streamed response (SSE) → frontend renders live
```

The agent loop is self-directing: the LLM decides when the data is sufficient to answer the user. It will follow up with JOIN queries if results contain unresolved foreign keys, retry with schema lookups if a table name is wrong, and only generate a final message when it is confident the data fully answers the question.

---

## Assumptions

- **Single database:** Both product and marketing schemas live in the same PostgreSQL instance.
- **Read-only:** The agent only executes `SELECT` statements. All write operations are blocked at the policy layer.
- **LLM API required:** No offline/local model fallback. At least one provider API key must be set.
- **Session identity is client-managed:** Sessions are identified by a UUID in a header or cookie. No authentication or user accounts.
- **Schema is ORM-defined:** The agent discovers tables and columns by introspecting SQLAlchemy models at runtime. Tables not mapped in the ORM are invisible to the agent.

## Limitations

- **No file export:** Query results are displayed in chat only. CSV export and pandas-based analytics are not yet implemented.
- **Row limit enforced:** Result sets are capped by policy (default 2000 rows). Large dataset exports are not supported.
- **Cache is per-session:** Response cache is keyed by `(session_id, normalized text)`. The same question from two different sessions will invoke the LLM twice.
- **No multi-database support:** Cross-instance joins (e.g. product and marketing from separate DB hosts) are not supported.
- **LLM non-determinism:** The agent may produce different SQL for the same question across runs. Query policy validation acts as a safety net but results are not guaranteed to be identical.
