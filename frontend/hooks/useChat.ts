"use client";

import { useRef, useState, useEffect } from "react";
import { predictStream, resetSession } from "@/api/predict";
import type { Message, UseChatReturn } from "@/types/chat";
import type { ProcessEvent, ToolCall } from "@/types/predict";

function formatArgs(args: Record<string, unknown> | undefined): string {
  if (!args) return "";
  return Object.entries(args)
    .map(([k, v]) => {
      const s = typeof v === "string" ? v : JSON.stringify(v);
      return `${k}: ${s.length > 80 ? s.slice(0, 80) + "…" : s}`;
    })
    .join(", ");
}

function sameStep(a: ProcessEvent, b: ProcessEvent): boolean {
  if (!a || !b) return false;
  if (a.id && b.id) return a.id === b.id;
  return a.stage === b.stage && a.title === b.title && a.detail === b.detail;
}

function dedupeSteps(steps: ProcessEvent[]): ProcessEvent[] {
  const out: ProcessEvent[] = [];
  for (const step of steps ?? []) {
    if (!step || typeof step !== "object") continue;
    if (!out.some((item) => sameStep(item, step))) out.push(step);
  }
  return out;
}

function stableStringify(value: unknown): string {
  const canonicalize = (input: unknown): unknown => {
    if (Array.isArray(input)) return input.map(canonicalize);
    if (input && typeof input === "object") {
      const src = input as Record<string, unknown>;
      const out: Record<string, unknown> = {};
      for (const key of Object.keys(src).sort()) {
        if (src[key] !== undefined) out[key] = canonicalize(src[key]);
      }
      return out;
    }
    return input ?? null;
  };
  try {
    return JSON.stringify(canonicalize(value));
  } catch {
    return "{}";
  }
}

function toolKey(tool: ToolCall): string {
  return `${tool.tool}::${stableStringify(tool.args)}`;
}

function dedupeToolCalls(calls: ToolCall[]): ToolCall[] {
  const map = new Map<string, ToolCall>();
  for (const call of calls) {
    if (!call || typeof call !== "object") continue;
    if (typeof call.tool !== "string") continue;
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

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
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

        const original = updated[targetIndex];
        if (!original) return prev;
        const msg = { ...original };
        fn(msg);
        updated[targetIndex] = msg;
        return updated;
      });
    };

    await predictStream(userMsg, {
      onExtraction: (extraction) => {
        if (!extraction || typeof extraction !== "object") return;
        update((msg) => {
          msg.extraction = extraction;
          const step: ProcessEvent = {
            stage: "intent_detected",
            title: "Intent detected",
            detail: typeof extraction.intent === "string" ? extraction.intent : "",
            timestamp: new Date().toISOString(),
            data: extraction,
          };
          const current = msg.process ?? [];
          if (!current.some((item) => item.stage === "intent_detected")) {
            msg.process = [...current, step];
          }
        });
      },
      onProcess: (step) => {
        if (!step || typeof step !== "object") return;
        update((msg) => {
          const current = msg.process ?? [];
          if (!current.some((item) => sameStep(item, step))) {
            msg.process = [...current, step];
          }
        });
      },
      onToolStart: (tool: ToolCall) => {
        if (!tool || typeof tool !== "object" || typeof tool.tool !== "string") return;
        update((msg) => {
          const calls = [...(msg.toolCalls ?? [])];
          const key = toolKey(tool);
          const idx = calls.findIndex((item) => toolKey(item) === key);
          if (idx >= 0) {
            calls[idx] = { ...calls[idx], ...tool, loading: true };
            msg.toolCalls = [...calls];
          } else {
            msg.toolCalls = [...calls, { ...tool, loading: true }];
          }
          const step: ProcessEvent = {
            stage: "tool_started",
            title: `Running ${tool.tool}`,
            detail: formatArgs(tool.args),
            timestamp: new Date().toISOString(),
          };
          const current = msg.process ?? [];
          if (!current.some((item) => sameStep(item, step))) {
            msg.process = [...current, step];
          }
        });
      },
      onToolEnd: (tool: ToolCall) => {
        if (!tool || typeof tool !== "object" || typeof tool.tool !== "string") return;
        update((msg) => {
          const calls = [...(msg.toolCalls ?? [])];
          const key = toolKey(tool);
          const idx = calls.findLastIndex((t) => toolKey(t) === key && t.loading);
          if (idx >= 0) {
            calls[idx] = { ...calls[idx], ...tool, loading: false };
            msg.toolCalls = dedupeToolCalls([...calls]);
          } else {
            const existingIdx = calls.findIndex((item) => toolKey(item) === key);
            if (existingIdx >= 0) {
              calls[existingIdx] = { ...calls[existingIdx], ...tool, loading: false };
              msg.toolCalls = dedupeToolCalls([...calls]);
            } else {
              msg.toolCalls = dedupeToolCalls([...calls, { ...tool, loading: false }]);
            }
          }
          const isError = (tool as unknown as Record<string, unknown>).error === true;
          const step: ProcessEvent = {
            stage: "tool_finished",
            title: `${tool.tool} done`,
            detail: isError ? "failed" : "",
            timestamp: new Date().toISOString(),
          };
          const current = msg.process ?? [];
          if (!current.some((item) => sameStep(item, step))) {
            msg.process = [...current, step];
          }
        });
      },
      onArtifact: (artifact) => {
        if (!artifact || typeof artifact !== "object") return;
        update((msg) => {
          const existing = msg.artifacts ?? [];
          const isDupe = existing.some(
            (a) =>
              a.type === artifact.type &&
              (artifact.type === "image"
                ? a.image?.slice(0, 32) === artifact.image?.slice(0, 32)
                : a.name === artifact.name),
          );
          if (!isDupe) msg.artifacts = [...existing, artifact];
        });
      },
      onMessage: (message: string) => {
        if (typeof message !== "string") return;
        update((msg) => { msg.content = (msg.content || "") + message; });
      },
      onResult: (result) => {
        if (!result || typeof result !== "object") return;
        update((msg) => {
          msg.result = result;
          // Keep frontend-synthesized tool steps (tool_started/tool_finished) — they're not in result.process
          const frontendSteps = (msg.process ?? []).filter(
            (s) => s.stage === "tool_started" || s.stage === "tool_finished",
          );
          msg.process = dedupeSteps([
            ...(Array.isArray(result.process) ? result.process : []),
            ...frontendSteps,
          ]);
          if (!(typeof msg.content === "string" && msg.content.trim().length > 0)) {
            if (typeof result.message === "string") msg.content = result.message;
          }
          const resultTools = Array.isArray(result.tool_results) ? result.tool_results : [];
          if (resultTools.length > 0) {
            const normalized = resultTools
              .filter((item): item is ToolCall => Boolean(item) && typeof item === "object")
              .map((item) => ({ ...item, loading: false }));
            msg.toolCalls = dedupeToolCalls([...(msg.toolCalls ?? []), ...normalized]);
          } else if (!Array.isArray(msg.toolCalls)) {
            msg.toolCalls = [];
          }
          // final result is authoritative — overwrite any duplicates from streaming
          if (Array.isArray(result.artifacts) && result.artifacts.length > 0) {
            msg.artifacts = result.artifacts;
          }
        });
      },
      onDone: () => {
        update((msg) => { msg.loading = false; });
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

  async function handleReset() {
    if (loading) return;
    await resetSession();
    setMessages([]);
  }

  return { input, setInput, messages, loading, bottomRef, handleSubmit, handleReset };
}
