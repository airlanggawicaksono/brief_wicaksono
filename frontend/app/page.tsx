"use client";

import { useChat } from "@/hooks/useChat";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";

export default function Home() {
  const {
    input,
    setInput,
    messages,
    loading,
    bottomRef,
    handleSubmit,
  } = useChat();

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      <div className="border-b border-gray-200 bg-white px-4 py-3">
        <h1 className="text-lg font-semibold">Brief</h1>
        <p className="text-xs text-gray-400">what eva</p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-gray-400">
              Type something to get started
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessage key={i} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      <ChatInput
        input={input}
        loading={loading}
        onInputChange={setInput}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
