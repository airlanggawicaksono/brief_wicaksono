import api from "@/api/base";
import type { Extraction, PredictResult, ProcessEvent, SSECallback, ToolCall } from "@/types/predict";

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
    else if (eventType === "message" && typeof data === "string") callbacks.onMessage?.(data);
    else if (eventType === "result" && isObject) callbacks.onResult(data as PredictResult);
    else if (eventType === "cached" && isObject) callbacks.onResult(data as PredictResult);
    else if (eventType === "done") callbacks.onDone();
  } catch {
    return { isDone: false };
  }

  return { isDone: eventType === "done" };
}

export async function predictStream(text: string, callbacks: SSECallback) {
  try {
    const sessionId = getSessionId();
    let processedLength = 0;
    let buffer = "";
    let hasDoneEvent = false;

    const response = await api.post<string>("/predict", { text }, {
      headers: {
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
        ...(sessionId ? { "X-Session-Id": sessionId } : {}),
      },
      responseType: "text",
      onDownloadProgress: (progressEvent) => {
        const target = progressEvent.event?.target as { responseText?: string } | null;
        const accumulated = target?.responseText ?? "";
        const newChunk = accumulated.slice(processedLength);
        processedLength = accumulated.length;

        buffer += newChunk;
        buffer = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";

        for (const chunk of chunks) {
          const { isDone } = handleEventChunk(chunk, callbacks);
          if (isDone) hasDoneEvent = true;
        }
      },
    });

    const serverSessionId = response.headers["x-session-id"];
    if (typeof serverSessionId === "string" && serverSessionId.trim()) {
      saveSessionId(serverSessionId.trim());
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
