"use client";

import { useRef, useState, useEffect } from "react";
import { predictStream } from "@/api/predict";
import type { Message, UseChatReturn } from "@/types/chat";

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
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    const assistantIndex = messages.length + 1;

    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", loading: true },
    ]);

    await predictStream(userMsg, {
      onExtraction: (extraction) => {
        setMessages((prev) => {
          const updated = [...prev];
          const msg = updated[assistantIndex];
          if (msg) msg.content = `Intent: ${extraction.intent}`;
          return updated;
        });
      },
      onResult: (result) => {
        setMessages((prev) => {
          const updated = [...prev];
          const msg = updated[assistantIndex];
          if (msg) {
            msg.result = result;
            msg.content = result.message || `Intent: ${result.extraction.intent}`;
          }
          return updated;
        });
      },
      onDone: () => {
        setMessages((prev) => {
          const updated = [...prev];
          const msg = updated[assistantIndex];
          if (msg) msg.loading = false;
          return updated;
        });
        setLoading(false);
      },
      onError: (err) => {
        setMessages((prev) => {
          const updated = [...prev];
          const msg = updated[assistantIndex];
          if (msg) {
            msg.content = `Error: ${err}`;
            msg.loading = false;
          }
          return updated;
        });
        setLoading(false);
      },
    });
  }

  return { input, setInput, messages, loading, bottomRef, handleSubmit };
}
