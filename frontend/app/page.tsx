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
    handleReset,
  } = useChat();

  return (
    <main className="flex h-screen flex-col bg-[#f9f9f9]">
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[48rem] px-4 py-6">
          {messages.length === 0 && (
            <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3">
              <h1 className="text-2xl font-semibold text-gray-800">
                Hi there, send message to start. What can I help with?
              </h1>
            </div>
          )}

          <div className="space-y-6">
            {messages.map((msg, i) => (
              <ChatMessage key={i} msg={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        </div>
      </div>

      <div className="shrink-0 border-t border-gray-200 bg-white px-4 pb-6 pt-4">
        <div className="mx-auto max-w-[48rem]">
          <ChatInput
            input={input}
            loading={loading}
            onInputChange={setInput}
            onSubmit={handleSubmit}
            onReset={handleReset}
          />
        </div>
      </div>
    </main>
  );
}
