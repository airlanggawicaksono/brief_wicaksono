import type { ChatInputProps } from "@/types/chat";

export function ChatInput({
  input,
  loading,
  onInputChange,
  onSubmit,
}: ChatInputProps) {
  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="Ask something..."
          className="flex-1 rounded-full border border-gray-300 px-4 py-2 text-sm focus:border-gray-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-full bg-gray-900 px-5 py-2 text-sm text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {loading ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
