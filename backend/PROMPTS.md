# Prompt Map

Every user message goes through two stages: **intent detection**, then **response**.

---

## Stage 1 — Intent Detection (always runs)

**File:** `app/prompts/intent_detection.py` → `INTENT_DETECTION_PROMPT`

Classifies the message into one of three intents:
- `data_query` — asks about products, audiences, campaigns, performance
- `general` — greeting, small talk, off-domain
- `clarification` — too vague to act on

---

## Stage 2 — Response (depends on intent)

### `data_query` → Agent path

**Prompts injected (in order):**
1. `app/prompts/tool_agent.py` → `TOOL_AGENT_PROMPT` — rules for tool use, schema discovery, query writing
2. `tool_context` (built at startup) — available tools + query constraints
3. `"User language hint: reply in the same language as this input -> {user_text}"` — dynamic, per-request
4. *(if entities)* extracted entities JSON from intent detection
5. *(if no entities but has history)* "This is a follow-up, use history context"
6. Chat history (user/assistant turns)
7. Current user message

**Code path:** `AgentResponseStrategy` → `AgentService.execute()` → `MessageBuilder.build()`

---

### `general` → Direct path

**Prompt injected:**
- `app/prompts/general.py` → `GENERAL_PROMPT` — stay in domain, explain capabilities, match user language

**Code path:** `DirectResponseStrategy._stream()`, no tools, single LLM stream call

---

### `clarification` → Direct path

**Prompt injected:**
- `app/prompts/clarification.py` → `CLARIFICATION_PROMPT` — ask one clarifying question, suggest 3 example queries, match user language

**Code path:** Same as `general` (`DirectResponseStrategy._stream()`), just different system prompt

---

## Summary

```
user message
    │
    ▼
INTENT_DETECTION_PROMPT
    │
    ├── data_query ──► TOOL_AGENT_PROMPT + tool_context + language hint + history
    │
    ├── general ─────► GENERAL_PROMPT + history
    │
    └── clarification ► CLARIFICATION_PROMPT + history
```
