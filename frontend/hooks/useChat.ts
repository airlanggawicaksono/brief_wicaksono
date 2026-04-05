"use client";

import { useRef, useState, useEffect } from "react";
import { predictStream } from "@/api/predict";
import type { Message, UseChatReturn } from "@/types/chat";
import type { ProcessStep, ToolResult } from "@/types/predict";

function sameStep(a: ProcessStep, b: ProcessStep): boolean {
  if (!a || !b) return false;
  return (
    a.stage === b.stage &&
    a.title === b.title &&
    a.detail === b.detail
  );
}

function dedupeSteps(steps: ProcessStep[]): ProcessStep[] {
  const out: ProcessStep[] = [];
  for (const step of steps ?? []) {
    if (!step || typeof step !== "object") continue;
    const exists = out.some((item) => sameStep(item, step));
    if (!exists) out.push(step);
  }
  return out;
}

function stableStringify(value: unknown): string {
  const canonicalize = (input: unknown): unknown => {
    if (Array.isArray(input)) {
      return input.map((item) => canonicalize(item));
    }
    if (input && typeof input === "object") {
      const source = input as Record<string, unknown>;
      const output: Record<string, unknown> = {};
      for (const key of Object.keys(source).sort()) {
        const raw = source[key];
        if (raw !== undefined) {
          output[key] = canonicalize(raw);
        }
      }
      return output;
    }
    return input ?? null;
  };

  try {
    return JSON.stringify(canonicalize(value));
  } catch {
    return "{}";
  }
}

function toolKey(tool: ToolResult): string {
  const name = typeof tool.tool === "string" ? tool.tool : "tool";
  return `${name}::${stableStringify(tool.args)}`;
}

function dedupeToolCalls(calls: ToolResult[]): ToolResult[] {
  const map = new Map<string, ToolResult>();
  for (const call of calls) {
    if (!call || typeof call !== "object") continue;
    if (!("tool" in call) || typeof call.tool !== "string") continue;
    map.set(toolKey(call), call);
  }
  return Array.from(map.values());
}

export function useChat(): UseChatReturn {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput("");
    setLoading(true);

    let assistantIndex = -1;
    setMessages((prev) => {
      assistantIndex = prev.length + 1;
      return [
        ...prev,
        { role: "user", content: userMsg },
        { role: "assistant", content: "", process: [], toolCalls: [], loading: true },
      ];
    });

    const update = (fn: (msg: Message) => void) => {
      setMessages((prev) => {
        const updated = [...prev];
        let targetIndex = assistantIndex;
        const isValidAssistant =
          targetIndex >= 0 &&
          targetIndex < updated.length &&
          updated[targetIndex]?.role === "assistant";

        if (!isValidAssistant) {
          targetIndex = updated.findLastIndex(
            (item) => item.role === "assistant" && item.loading,
          );
        }

        if (targetIndex < 0 || targetIndex >= updated.length) return prev;
        assistantIndex = targetIndex;

        const msg = updated[targetIndex];
        if (!msg) return prev;
        fn(msg);
        return updated;
      });
    };

    await predictStream(userMsg, {
      onExtraction: (extraction) => {
        if (!extraction || typeof extraction !== "object") return;
        update((msg) => {
          msg.extraction = extraction;
        });
      },
      onProcess: (step) => {
        if (!step || typeof step !== "object") return;
        update((msg) => {
          const current = msg.process ?? [];
          const exists = current.some((item) => sameStep(item, step));
          if (!exists) {
            msg.process = [...current, step];
          }
        });
      },
      onToolStart: (tool: ToolResult) => {
        if (!tool || typeof tool !== "object") return;
        if (!("tool" in tool) || typeof tool.tool !== "string") return;
        update((msg) => {
          const calls = msg.toolCalls ?? [];
          const key = toolKey(tool);
          const existingIndex = calls.findIndex((item) => toolKey(item) === key);
          if (existingIndex >= 0) {
            calls[existingIndex] = { ...calls[existingIndex], ...tool, loading: true };
            msg.toolCalls = [...calls];
            return;
          }

          msg.toolCalls = [...calls, { ...tool, loading: true }];
        });
      },
      onToolEnd: (tool: ToolResult) => {
        if (!tool || typeof tool !== "object") return;
        if (!("tool" in tool) || typeof tool.tool !== "string") return;
        update((msg) => {
          const calls = msg.toolCalls ?? [];
          const key = toolKey(tool);
          const idx = calls.findLastIndex((t) => toolKey(t) === key && t.loading);
          if (idx >= 0) {
            calls[idx] = { ...calls[idx], ...tool, loading: false };
            msg.toolCalls = dedupeToolCalls([...calls]);
          } else {
            const existingIndex = calls.findIndex((item) => toolKey(item) === key);
            if (existingIndex >= 0) {
              calls[existingIndex] = { ...calls[existingIndex], ...tool, loading: false };
              msg.toolCalls = dedupeToolCalls([...calls]);
              return;
            }
            msg.toolCalls = dedupeToolCalls([...calls, { ...tool, loading: false }]);
          }
        });
      },
      onMessage: (message: string) => {
        if (typeof message !== "string") return;
        update((msg) => {
          msg.content = message;
        });
      },
      onResult: (result) => {
        if (!result || typeof result !== "object") return;
        update((msg) => {
          msg.result = result;
          msg.process = dedupeSteps(Array.isArray(result.process) ? result.process : []);
          const hasStreamedContent =
            typeof msg.content === "string" && msg.content.trim().length > 0;
          if (!hasStreamedContent && typeof result.message === "string") {
            msg.content = result.message;
          }

          const resultTools = Array.isArray(result.tool_results) ? result.tool_results : [];
          if (resultTools.length > 0) {
            const normalizedResultTools = resultTools
              .filter((item): item is ToolResult => Boolean(item) && typeof item === "object")
              .map((item) => ({ ...item, loading: false }));
            msg.toolCalls = dedupeToolCalls([...(msg.toolCalls ?? []), ...normalizedResultTools]);
          } else if (!Array.isArray(msg.toolCalls)) {
            msg.toolCalls = [];
          }
        });
      },
      onDone: () => {
        update((msg) => {
          msg.loading = false;
        });
        setLoading(false);
      },
      onError: (err) => {
        update((msg) => {
          msg.content = `Error: ${err}`;
          msg.loading = false;
        });
        setLoading(false);
      },
    });
  }

  return { input, setInput, messages, loading, bottomRef, handleSubmit };
}
