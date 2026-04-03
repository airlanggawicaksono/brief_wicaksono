import api from "./base";
import type { SSECallback } from "@/types/predict";

export async function predictStream(text: string, callbacks: SSECallback) {
  try {
    const res = await api.post("/predict", { text }, { responseType: "stream", adapter: "fetch" });

    const reader = (res.data as ReadableStream).getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let eventType = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7);
        } else if (line.startsWith("data: ")) {
          const data = JSON.parse(line.slice(6));
          if (eventType === "extraction") callbacks.onExtraction?.(data);
          else if (eventType === "tool_result") callbacks.onToolResult?.(data);
          else if (eventType === "result") callbacks.onResult(data);
          else if (eventType === "cached") callbacks.onResult(data);
          else if (eventType === "done") callbacks.onDone();
        }
      }
    }
  } catch (err) {
    callbacks.onError?.(err instanceof Error ? err.message : "Request failed");
  }
}

export async function fetchHistory(limit: number = 50) {
  const res = await api.get("/predict/history", { params: { limit } });
  return res.data;
}
