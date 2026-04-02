export interface Entities {
  category: string | null;
  target: string | null;
  price_max: number | null;
}

export interface PredictResult {
  intent: string;
  entities: Entities;
}

export type SSECallback = {
  onToken: (content: string) => void;
  onResult: (result: PredictResult) => void;
  onDone: () => void;
  onError?: (error: string) => void;
};
