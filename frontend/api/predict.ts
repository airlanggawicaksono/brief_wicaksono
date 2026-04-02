import { apiFetch } from "./base";
import type { PredictResult } from "@/types/predict";

export async function predict(text: string): Promise<PredictResult> {
  return apiFetch<PredictResult>("/predict", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}
