// Freeform K:V — any key the LLM extracts is valid
export type Entities = Record<string, string | number | boolean | null>;

// Matches backend PredictResponse — entities only present for data_query
export interface Extraction {
  intent: string;
  entities: Entities | null;
}

// Matches the `event: process` SSE payload from SsePresenter._process_event()
export interface ProcessEvent {
  id?: string;     // backend-generated hex UUID — use for dedup when present
  stage: string;
  title: string;
  detail: string;
  timestamp: string;
  // Present in result.process (full ProcessEvent from backend), absent in SSE stream
  type?: string;
  data?: unknown;
}

// Matches `event: tool_start` / `event: tool_end` payloads from SsePresenter._tool_event()
// and also the error shape from _compact_for_ui when is_error=True
export interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  // tool_end with data
  data?: unknown;
  // error shape: {tool, args, error: true, message: "..."}
  error?: true;
  message?: string;
  // frontend-only loading state
  loading?: boolean;
}

// Matches backend PredictResult
export interface PredictResult {
  input: string;
  extraction: Extraction;
  mode: string;
  tool_results: ToolCall[];
  process: ProcessEvent[];
  message: string;
}

export type SSECallback = {
  onExtraction?: (extraction: Extraction) => void;
  onProcess?: (step: ProcessEvent) => void;
  onToolStart?: (tool: ToolCall) => void;
  onToolEnd?: (tool: ToolCall) => void;
  onMessage?: (message: string) => void;
  onResult: (result: PredictResult) => void;
  onDone: () => void;
  onError?: (error: string) => void;
};
