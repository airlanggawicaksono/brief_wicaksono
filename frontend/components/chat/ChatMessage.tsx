import type { ChatMessageProps } from "@/types/chat";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

type JsonObject = Record<string, unknown>;
type TableData = { columns: string[]; rows: JsonObject[] };

function isPlainObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function safeValue(value: unknown, maxLen: number = 160): string {
  if (value == null) return "-";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);

  try {
    const serialized = JSON.stringify(value);
    if (!serialized) return "-";
    return serialized.length > maxLen ? `${serialized.slice(0, maxLen)}...` : serialized;
  } catch {
    return String(value);
  }
}

function collectColumns(rows: JsonObject[]): string[] {
  const cols: string[] = [];
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (!cols.includes(key)) cols.push(key);
    }
  }
  return cols;
}

function tableFromArray(data: unknown[]): TableData {
  if (data.length === 0) {
    return { columns: ["value"], rows: [] };
  }

  const allObjects = data.every((item) => isPlainObject(item));
  if (allObjects) {
    const rows = data as JsonObject[];
    return { columns: collectColumns(rows), rows };
  }

  return {
    columns: ["value"],
    rows: data.map((value) => ({ value })),
  };
}

function schemaTableFromObject(data: JsonObject): TableData | null {
  const tables = data.tables;
  const rows: JsonObject[] = [];

  if (Array.isArray(tables)) {
    for (const item of tables) {
      if (!isPlainObject(item)) continue;
      const columnNamesRaw = Array.isArray(item.columns) ? item.columns : [];
      const columnNames = columnNamesRaw.filter((entry): entry is string => typeof entry === "string");
      rows.push({
        table: typeof item.table === "string" ? item.table : "",
        domain: typeof item.domain === "string" ? item.domain : "",
        column_count:
          typeof item.column_count === "number" ? item.column_count : columnNames.length,
        columns: columnNames.join(", "),
      });
    }
  } else if (isPlainObject(tables)) {
    for (const [tableName, meta] of Object.entries(tables)) {
      if (!isPlainObject(meta)) continue;

      const columnNamesRaw = Array.isArray(meta.column_names)
        ? meta.column_names
        : Array.isArray(meta.columns)
          ? meta.columns
          : [];
      const columnNames = columnNamesRaw.filter((item): item is string => typeof item === "string");

      rows.push({
        table: tableName,
        domain: typeof meta.domain === "string" ? meta.domain : "",
        column_count:
          typeof meta.column_count === "number" ? meta.column_count : columnNames.length,
        columns: columnNames.join(", "),
      });
    }
  } else {
    return null;
  }

  if (rows.length === 0) return null;

  return {
    columns: ["table", "domain", "column_count", "columns"],
    rows,
  };
}

function toTableData(data: unknown): TableData | null {
  if (Array.isArray(data)) {
    return tableFromArray(data);
  }

  if (isPlainObject(data)) {
    const schemaTable = schemaTableFromObject(data);
    if (schemaTable) return schemaTable;

    if (Array.isArray(data.rows)) {
      return tableFromArray(data.rows);
    }

    const entries = Object.entries(data);
    if (entries.length === 0) return null;

    return {
      columns: ["field", "value"],
      rows: entries.map(([field, value]) => ({ field, value })),
    };
  }

  return null;
}

export function ChatMessage({ msg }: ChatMessageProps) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-3xl bg-gray-100 px-5 py-3 text-sm text-gray-900">
          <p>{msg.content}</p>
        </div>
      </div>
    );
  }

  const extraction = msg.extraction ?? msg.result?.extraction;
  const toolCallsRaw = msg.toolCalls ?? msg.result?.tool_results;
  const processRaw = msg.process ?? msg.result?.process;
  const toolCalls = Array.isArray(toolCallsRaw) ? toolCallsRaw : [];
  const process = Array.isArray(processRaw) ? processRaw : [];
  const entities =
    extraction &&
    typeof extraction === "object" &&
    extraction.entities &&
    typeof extraction.entities === "object"
      ? {
        category: extraction.entities.category ?? null,
        target: extraction.entities.target ?? null,
        price_max: extraction.entities.price_max ?? null,
      }
      : null;
  const entityPairs: Array<[string, unknown]> = entities
    ? [
      ["category", entities.category ?? null],
      ["target", entities.target ?? null],
      ["price_max", entities.price_max ?? null],
    ]
    : [];

  return (
    <div className="flex gap-3">
      <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-900 text-xs font-bold text-white">
        W
      </div>

      <div className="min-w-0 flex-1 space-y-3">
        {entityPairs.some(([, value]) => value != null) && (
          <div className="flex flex-wrap items-center gap-2">
            {entityPairs.map(([key, value]) =>
              value != null ? (
                <span
                  key={key}
                  className="rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                >
                  {key}:{" "}
                  <span className="font-medium text-gray-900">
                    {String(value)}
                  </span>
                </span>
              ) : null,
            )}
          </div>
        )}

        {process.length > 0 && (
          <div className="space-y-1 text-xs text-gray-400">
            {process
              .filter((step) => {
                if (!step || typeof step !== "object") return false;
                const stage = typeof step.stage === "string" ? step.stage : "";
                if (stage === "failed") return false;
                if (stage === "response_ready") return false;
                return true;
              })
              .map((step, i) => {
                const stage = typeof step.stage === "string" ? step.stage : `step-${i}`;
                const title = typeof step.title === "string" ? step.title : "Step";
                const detail = typeof step.detail === "string" ? step.detail : "";

                return (
                  <div key={`${stage}-${i}`} className="flex items-center gap-2">
                    <span className="h-1 w-1 shrink-0 rounded-full bg-gray-300" />
                    <span>{title}</span>
                    {detail && <span className="text-gray-300">{detail}</span>}
                  </div>
                );
              })}
          </div>
        )}

        {toolCalls.length > 0 && (
          <div className="space-y-2">
            {toolCalls
              .filter((tc) => {
                if (!tc || typeof tc !== "object") return false;
                const raw = tc as unknown as JsonObject;
                if (raw.error === true) return false;
                return true;
              })
              .map((tc, i) => {
                const toolName = typeof tc.tool === "string" ? tc.tool : "tool";
                const isLoading = Boolean(tc.loading);
                const hasData = tc.data !== null && tc.data !== undefined;

                let preview = "";
                if (hasData) {
                  try {
                    preview = JSON.stringify(tc.data, null, 2).slice(0, 500);
                  } catch {
                    preview = String(tc.data);
                  }
                }
                const tableData = hasData ? toTableData(tc.data) : null;

                return (
                  <details
                    key={`${toolName}-${i}`}
                    className="rounded-xl border border-gray-200 bg-gray-50/50"
                    open={isLoading}
                  >
                    <summary className="flex cursor-pointer select-none items-center gap-2 px-3 py-2 text-xs">
                      {isLoading ? (
                        <span className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-amber-400" />
                      ) : (
                        <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-400" />
                      )}
                      <span className="font-medium text-gray-700">{toolName}</span>
                      {!isLoading && hasData && (
                        <span className="text-gray-400">
                          {Array.isArray(tc.data)
                            ? `${tc.data.length} row${tc.data.length !== 1 ? "s" : ""}`
                            : "done"}
                        </span>
                      )}
                      {isLoading && <span className="text-gray-400">running...</span>}
                    </summary>
                    {!isLoading && hasData && (
                      <div className="border-t border-gray-100 px-3 py-2 text-xs text-gray-500">
                        {tableData ? (
                          <div className="overflow-auto rounded-md border border-gray-200">
                            {tableData.rows.length === 0 ? (
                              <div className="px-3 py-2 text-xs text-gray-400">No rows</div>
                            ) : (
                              <table className="min-w-full border-collapse text-left text-xs">
                                <thead className="bg-gray-100 text-gray-600">
                                  <tr>
                                    {tableData.columns.map((column) => (
                                      <th key={column} className="border-b border-gray-200 px-2 py-1.5 font-medium">
                                        {column}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody className="text-gray-700">
                                  {tableData.rows.map((row, rowIndex) => (
                                    <tr key={`${toolName}-row-${rowIndex}`} className="border-b border-gray-100 last:border-b-0">
                                      {tableData.columns.map((column) => (
                                        <td key={`${toolName}-${rowIndex}-${column}`} className="max-w-[280px] px-2 py-1.5 align-top">
                                          <span className="line-clamp-4 break-words">
                                            {safeValue(row[column])}
                                          </span>
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            )}
                          </div>
                        ) : (
                          <pre className="max-h-40 overflow-auto whitespace-pre-wrap">
                            {preview}
                          </pre>
                        )}
                      </div>
                    )}
                  </details>
                );
              })}
          </div>
        )}

        {msg.loading && !msg.content && toolCalls.length === 0 && (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-gray-400" />
            Processing...
          </div>
        )}

        {msg.content && (
          <div className="chat-markdown text-sm leading-relaxed text-gray-800">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                a: ({ ...props }) => (
                  <a
                    {...props}
                    className="text-blue-600 underline underline-offset-2 hover:text-blue-700"
                    target="_blank"
                    rel="noreferrer noopener"
                  />
                ),
                code: ({ className, children, ...props }) => {
                  const isBlock = Boolean(className);
                  if (isBlock) {
                    return (
                      <code
                        {...props}
                        className="block overflow-x-auto rounded-md bg-gray-900 px-3 py-2 text-xs text-gray-100"
                      >
                        {children}
                      </code>
                    );
                  }

                  return (
                    <code
                      {...props}
                      className="rounded bg-gray-100 px-1 py-0.5 text-[0.85em] text-gray-800"
                    >
                      {children}
                    </code>
                  );
                },
              }}
            >
              {msg.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
