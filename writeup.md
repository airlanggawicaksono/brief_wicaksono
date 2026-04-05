SYSTEM DESIGN OF AN MVP WPP BRIEF CHATBOT

1. Overview of the System design and Structure
A natural language interface for marketing analytics. Users type plain text; the system detects intent, queries a relational database if needed, and streams a human-readable response back in real time using a simplex connection through SSE.

Figure 1.1. Business process of the Proposed Application

Figure 1.1 shows a layered backend where Redis manages conversation state and a ReAct loop drives the core logic, iteratively selecting and executing tools from the service layer to fulfil user intent. The backend is a FastAPI application split into four layers: API, Services, Policy, and Repository. Each layer has one job and dependencies only flow downward. The service layer contains the tools the agent can call. The policy layer enforces SQL safety and intent validation. The repository layer handles Redis for chat history and response caching.

backend/
  app/
    api/          - routes and dependency injection
    services/     - business logic (predict, agent, intent, tools)
    policy/       - query validation, intent normalisation, tool allowlist
    repository/   - Redis chat memory
    prompts/      - LLM system prompts
    core/         - enums, exceptions, provider factory, infra utilities
Figure 1.2. System Layer Structure

The frontend is Next.js 15 with React 19. It receives the SSE stream via axios onDownloadProgress instead of the native EventSource API, which only supports GET. Since the predict endpoint is a POST, this lets the request body carry the user text while still streaming the response live.


2. Agent Loop, Extensibility, and Design Decisions
Every request starts with intent detection. The LLM returns a structured result with two fields: intent, which is always one of data_query, general, or clarification, and entities, which are freeform key-value pairs extracted from the message.

{
  "intent": "data_query",
  "entities": {
    "brand": "Wardah",
    "date_range": "current month"
  }
}
Figure 2.1. The output of Intent Detection Service Module

Unexpected intent values are normalised to clarification by policy instead of crashing. From there, data_query goes to the agent and everything else gets a direct LLM response. The policy layer uses pure dataclasses with no framework dependencies, and the service layer depends on abstractions so the LLM provider can be swapped with one environment variable change.

The agent loop is a straightforward iteration. The LLM receives the full conversation, calls a tool or responds, and if it calls a tool the result is fed back for the next round. This repeats until the LLM stops calling tools. The loop is capped at 25 rounds. Before the loop starts, the MessageBuilder assembles the context the LLM will work with. It injects two things on top of the base system prompt. First, a tool context block built directly from the live tool objects and the active query policy:

tool_lines = [f"- {t.name}: {t.description}" for t in tools]

Figure 2.2. Tool context is derived directly from tool objects at runtime

To add a new tool to the agent, you only need to add the tool object to the list. No prompt edits, no config files, no registration steps. Second, if the intent step extracted entities, those are injected as a hint to steer the agent toward more relevant queries without hardcoding any filtering logic in Python. Extensibility works the same way for tool definitions. A tool is one Python function with a typed signature and a docstring. From that single definition, the LangChain framework generates the JSON Schema the LLM API uses to enforce correct argument types, the description the LLM reads to decide when to call the tool, and the line that appears in the tool context block. Nothing is written twice.


3. Handling of AI Uncertainty
Unreliable LLM output is handled at three points. Intent detection uses structured output so the result is always a typed Pydantic model, and any unrecognised intent is normalised to clarification by policy. Every generated SQL query goes through sqlglot validation before reaching the database, blocking write operations, unknown tables, and results over the row limit. Inside the agent loop, the system prompt instructs the LLM to evaluate its own tool results rather than Python checking for specific failure patterns, which means the same logic applies regardless of how many tools exist.


4. Trade-offs

The agent evaluates its own output quality through the system prompt rather than Python checking for specific failure patterns. This scales to any number of tools without code changes, but it introduces non-determinism. The same query can produce different SQL across runs, and whether the LLM decides to do a JOIN or not depends on how well the prompt is written.

Intent detection is a separate LLM call before the agent runs. This adds one round-trip of latency on every request. The benefit is that the classification step is independently testable and can be swapped or improved without touching the agent at all.

A hand-rolled ReAct loop is used instead of LangGraph. This keeps the control flow explicit and easy to follow, but the current loop has no native support for conditional branching or structured retry logic. Adding tools like subprocess or file export that depend on prior tool outputs will need careful prompt engineering to sequence correctly, whereas LangGraph would handle that more formally.

Schema discovery uses ORM introspection at runtime so schema changes are automatically visible to the agent. The constraint is that only tables mapped in the ORM exist from the agent's perspective. Any table outside the ORM is invisible by design, which is intentional for safety but means the agent cannot be extended to new tables without a code change.
