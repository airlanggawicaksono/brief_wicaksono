export interface Entities {
  category: string | null;
  target: string | null;
  price_max: number | null;
}

export interface PredictResult {
  intent: string;
  entities: Entities;
}
