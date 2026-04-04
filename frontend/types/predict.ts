export interface Entities {
  category: string | null;
  target: string | null;
  price_max: number | null;
}

export interface Extraction {
  intent: string;
  entities: Entities;
}

export interface ProcessStep {
  stage: string;
  title: string;
  detail: string;
  timestamp: string;
}

export interface ToolResult {
  tool: string;
  args: Record<string, unknown>;
  data: Record<string, unknown>[] | Record<string, unknown> | unknown[] | string | number | boolean | null;
  loading?: boolean;
}

export interface PredictResult {
  pipeline_version: number;
  input: string;
  extraction: Extraction;
  mode: string;
  tool_results: ToolResult[];
  process: ProcessStep[];
  message: string;
  metadata_snapshot_hash?: string | null;
  metadata_snapshot_version?: string | null;
}

export type SSECallback = {
  onExtraction?: (extraction: Extraction) => void;
  onProcess?: (step: ProcessStep) => void;
  onToolStart?: (tool: ToolResult) => void;
  onToolEnd?: (tool: ToolResult) => void;
  onMessage?: (message: string) => void;
  onResult: (result: PredictResult) => void;
  onDone: () => void;
  onError?: (error: string) => void;
};
