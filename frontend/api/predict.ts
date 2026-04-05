import type { Extraction, PredictResult, ProcessStep, SSECallback, ToolResult } from "@/types/predict";

const SESSION_STORAGE_KEY = "wpp_session_id";

function getSessionId(): string | null {
  if (typeof window === "undefined") return null;

  let sessionId = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (!sessionId) {
    sessionId = window.crypto?.randomUUID?.() ?? `${Date.now()}`;
    window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }

  return sessionId;
}

function saveSessionIdFromHeaders(headers: unknown): void {
  if (typeof window === "undefined" || !headers) return;

  let sessionId: string | null = null;
  try {
    if (typeof headers === "object" && headers !== null && "get" in headers) {
      const getter = (headers as { get?: (name: string) => string | null }).get;
      const raw = typeof getter === "function" ? getter("x-session-id") : null;
      if (typeof raw === "string" && raw.trim().length > 0) {
        sessionId = raw.trim();
      }
    } else if (typeof headers === "object" && headers !== null) {
      const raw = (headers as Record<string, unknown>)["x-session-id"];
      if (typeof raw === "string" && raw.trim().length > 0) {
        sessionId = raw.trim();
      }
    }
  } catch {
    return;
  }

  if (sessionId) {
    window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }
}

function handleEventChunk(
  chunk: string,
  callbacks: SSECallback,
): { isDone: boolean; eventType: string } {
  const lines = chunk
    .split("\n")
    .map((line) => line.replace(/\r$/, ""))
    .filter((line) => line.length > 0);

  if (lines.length === 0) return { isDone: false, eventType: "" };

  let eventType = "";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  if (!eventType || dataLines.length === 0) return { isDone: false, eventType: "" };

  const dataRaw = dataLines.join("\n");
  try {
    const data: unknown = JSON.parse(dataRaw);
    const isObject = typeof data === "object" && data !== null;

    if (eventType === "extraction") {
      if (isObject) callbacks.onExtraction?.(data as Extraction);
    } else if (eventType === "process") {
      if (isObject) callbacks.onProcess?.(data as ProcessStep);
    } else if (eventType === "tool_start") {
      if (isObject) callbacks.onToolStart?.(data as ToolResult);
    } else if (eventType === "tool_end") {
      if (isObject) callbacks.onToolEnd?.(data as ToolResult);
    } else if (eventType === "message") {
      if (typeof data === "string") callbacks.onMessage?.(data);
    } else if (eventType === "result") {
      if (isObject) callbacks.onResult(data as PredictResult);
    } else if (eventType === "cached") {
      if (isObject) callbacks.onResult(data as PredictResult);
    }
    else if (eventType === "done") callbacks.onDone();
  } catch {
    return { isDone: false, eventType: "" };
  }

  return { isDone: eventType === "done", eventType };
}

export async function predictStream(text: string, callbacks: SSECallback) {
  try {
    const sessionId = getSessionId();
    const base = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
    const endpoint = `${base}/predict`;

    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        ...(sessionId ? { "X-Session-Id": sessionId } : {}),
      },
      body: JSON.stringify({ text }),
      credentials: "include",
    });

    if (!res.ok) {
      throw new Error(`Request failed with status ${res.status}`);
    }

    saveSessionIdFromHeaders(res.headers);

    if (!res.body) {
      const fallback = await res.text();
      if (fallback && callbacks.onMessage) callbacks.onMessage(fallback);
      callbacks.onDone();
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let hasDoneEvent = false;
    const MESSAGE_CHUNK_PAINT_DELAY_MS = 8;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";

      for (const chunk of chunks) {
        const { isDone, eventType } = handleEventChunk(chunk, callbacks);
        hasDoneEvent = isDone || hasDoneEvent;
        if (eventType === "message") {
          await new Promise((resolve) => setTimeout(resolve, MESSAGE_CHUNK_PAINT_DELAY_MS));
        }
      }
    }

    buffer += decoder.decode();
    buffer = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

    if (buffer.trim().length > 0) {
      const { isDone, eventType } = handleEventChunk(buffer, callbacks);
      hasDoneEvent = isDone || hasDoneEvent;
      if (eventType === "message") {
        await new Promise((resolve) => setTimeout(resolve, MESSAGE_CHUNK_PAINT_DELAY_MS));
      }
    }

    if (!hasDoneEvent) {
      callbacks.onDone();
    }
  } catch (err) {
    console.error("predictStream error:", err);
    callbacks.onError?.(err instanceof Error ? err.message : "Request failed");
  }
}
