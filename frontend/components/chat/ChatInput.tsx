import type { ChatInputProps } from "@/types/chat";

export function ChatInput({
  input,
  loading,
  onInputChange,
  onSubmit,
}: ChatInputProps) {
  return (
    <form onSubmit={onSubmit} className="relative">
      <input
        type="text"
        value={input}
        onChange={(e) => onInputChange(e.target.value)}
        placeholder="Message..."
        className="w-full rounded-2xl border border-gray-300 bg-white px-4 py-3.5 pr-14 text-sm text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-gray-400 focus:ring-1 focus:ring-gray-400"
      />
      <button
        type="submit"
        disabled={loading || !input.trim()}
        className="absolute right-2 top-1/2 -translate-y-1/2 rounded-xl bg-gray-900 p-2 text-white transition hover:bg-gray-700 disabled:bg-gray-300 disabled:text-gray-500"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M3 13L13 3M13 3H5M13 3V11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </form>
  );
}
