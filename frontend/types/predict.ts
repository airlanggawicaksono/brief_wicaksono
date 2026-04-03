export interface Entities {
  category: string | null;
  target: string | null;
  price_max: number | null;
}

export interface Extraction {
  intent: string;
  entities: Entities;
}

export interface ToolResult {
  tool: string;
  args: Record<string, unknown>;
  data: Record<string, unknown>[] | unknown;
}

export interface PredictResult {
  input: string;
  extraction: Extraction;
  tool_results: ToolResult[];
  message: string;
}

export type SSECallback = {
  onExtraction?: (extraction: Extraction) => void;
  onToolResult?: (toolOutput: { tool_results: ToolResult[]; message: string }) => void;
  onResult: (result: PredictResult) => void;
  onDone: () => void;
  onError?: (error: string) => void;
};
