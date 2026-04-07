import api from "@/api/base";
import type { Artifact, Extraction, PredictResult, ProcessEvent, SSECallback, ToolCall } from "@/types/predict";

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

function saveSessionId(id: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(SESSION_STORAGE_KEY, id);
}

function handleEventChunk(
  chunk: string,
  callbacks: SSECallback,
): { isDone: boolean } {
  const lines = chunk
    .split("\n")
    .map((line) => line.replace(/\r$/, ""))
    .filter((line) => line.length > 0);

  if (lines.length === 0) return { isDone: false };

  let eventType = "";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  if (!eventType || dataLines.length === 0) return { isDone: false };

  try {
    const data: unknown = JSON.parse(dataLines.join("\n"));
    const isObject = typeof data === "object" && data !== null;

    if (eventType === "extraction" && isObject) callbacks.onExtraction?.(data as Extraction);
    else if (eventType === "process" && isObject) callbacks.onProcess?.(data as ProcessEvent);
    else if (eventType === "tool_start" && isObject) callbacks.onToolStart?.(data as ToolCall);
    else if (eventType === "tool_end" && isObject) callbacks.onToolEnd?.(data as ToolCall);
    else if (eventType === "artifact" && isObject) callbacks.onArtifact?.(data as Artifact);
    else if (eventType === "message" && typeof data === "string") callbacks.onMessage?.(data);
    else if (eventType === "result" && isObject) callbacks.onResult(data as PredictResult);
    else if (eventType === "cached" && isObject) callbacks.onResult(data as PredictResult);
    else if (eventType === "done") callbacks.onDone();
  } catch {
    return { isDone: false };
  }

  return { isDone: eventType === "done" };
}

export async function resetSession(): Promise<void> {
  const sessionId = getSessionId();
  await api.delete("/predict/session", {
    headers: sessionId ? { "X-Session-Id": sessionId } : {},
  });
  // generate a fresh session id so the next request starts completely clean
  const newId = window.crypto?.randomUUID?.() ?? `${Date.now()}`;
  saveSessionId(newId);
}

export async function predictStream(text: string, callbacks: SSECallback) {
  try {
    const sessionId = getSessionId();
    let buffer = "";
    let hasDoneEvent = false;

    const baseURL = process.env.NEXT_PUBLIC_API_URL ?? "";
    const response = await fetch(`${baseURL}/predict`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
        ...(sessionId ? { "X-Session-Id": sessionId } : {}),
      },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Request failed with status ${response.status}`);
    }

    const serverSessionId = response.headers.get("x-session-id");
    if (serverSessionId && serverSessionId.trim()) {
      saveSessionId(serverSessionId.trim());
    }

    if (!response.body) {
      throw new Error("Streaming response body is empty");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() ?? "";

      for (const chunk of chunks) {
        const { isDone } = handleEventChunk(chunk, callbacks);
        if (isDone) hasDoneEvent = true;
      }
    }

    const tail = decoder.decode();
    if (tail) {
      buffer += tail;
    }

    if (buffer.trim()) {
      const { isDone } = handleEventChunk(buffer, callbacks);
      if (isDone) hasDoneEvent = true;
    }

    if (!hasDoneEvent) callbacks.onDone();
  } catch (err: unknown) {
    callbacks.onError?.(err instanceof Error ? err.message : "Request failed");
  }
}
