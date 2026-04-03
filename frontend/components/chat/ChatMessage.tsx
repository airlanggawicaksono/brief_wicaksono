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

  const extraction = msg.result?.extraction;
  const toolResults = msg.result?.tool_results ?? [];

  return (
    <div className="flex justify-start">
      <div className="max-w-[75%] rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-800">
        {msg.loading && !msg.content && (
          <span className="text-gray-400">...</span>
        )}

        {msg.content && <p>{msg.content}</p>}

        {extraction && (
          <div className="mt-2 space-y-2 border-t border-gray-100 pt-2">
            <div>
              <span className="text-xs font-semibold text-gray-400">INTENT</span>
              <p className="font-medium">{extraction.intent}</p>
            </div>
            {Object.entries(extraction.entities).some(([, v]) => v != null) && (
              <div>
                <span className="text-xs font-semibold text-gray-400">ENTITIES</span>
                <dl className="mt-0.5 space-y-0.5">
                  {Object.entries(extraction.entities).map(([key, value]) =>
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

        {toolResults.length > 0 && (
          <div className="mt-2 space-y-2 border-t border-gray-100 pt-2">
            {toolResults.map((tr, i) => (
              <div key={i}>
                <span className="text-xs font-semibold text-gray-400">
                  {tr.tool.toUpperCase()}
                </span>
                {Array.isArray(tr.data) ? (
                  <div className="mt-1 space-y-1">
                    {tr.data.map((item, j) => (
                      <div key={j} className="rounded bg-gray-50 px-2 py-1 text-xs">
                        {Object.entries(item as Record<string, unknown>).map(([k, v]) => (
                          <span key={k} className="mr-2">
                            <span className="text-gray-500">{k}:</span> {String(v)}
                          </span>
                        ))}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs">{JSON.stringify(tr.data)}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
