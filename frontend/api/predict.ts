import type { SSECallback } from "@/types/predict";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8037";

export async function predictStream(text: string, callbacks: SSECallback) {
  const res = await fetch(`${API_URL}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!res.ok || !res.body) {
    callbacks.onError?.(`API error ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
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
        if (eventType === "token") callbacks.onToken(data.content);
        else if (eventType === "result") callbacks.onResult(data);
        else if (eventType === "done") callbacks.onDone();
      }
    }
  }
}
