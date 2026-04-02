import type { ChatMessageProps } from "@/types/chat";

export function ChatMessage({ msg }: ChatMessageProps) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl bg-gray-900 px-4 py-2.5 text-sm text-white">
          <p>{msg.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[75%] rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-800">
        {msg.content && (
          <pre className="whitespace-pre-wrap font-mono text-xs">
            {msg.content}
          </pre>
        )}

        {msg.streaming && !msg.content && (
          <span className="text-gray-400">...</span>
        )}

        {msg.result && (
          <div className="mt-2 space-y-2 border-t border-gray-100 pt-2">
            <div>
              <span className="text-xs font-semibold text-gray-400">
                INTENT
              </span>
              <p className="font-medium">{msg.result.intent}</p>
            </div>
            {Object.entries(msg.result.entities).some(
              ([, v]) => v != null
            ) && (
              <div>
                <span className="text-xs font-semibold text-gray-400">
                  ENTITIES
                </span>
                <dl className="mt-0.5 space-y-0.5">
                  {Object.entries(msg.result.entities).map(([key, value]) =>
                    value != null ? (
                      <div key={key} className="flex gap-1.5 text-xs">
                        <dt className="text-gray-500">{key}:</dt>
                        <dd>{String(value)}</dd>
                      </div>
                    ) : null
                  )}
                </dl>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
