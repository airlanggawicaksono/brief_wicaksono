"use client";

import { useState } from "react";
import { predictStream } from "@/api/predict";
import type { PredictResult } from "@/types/predict";

export default function Home() {
  const [input, setInput] = useState("");
  const [tokens, setTokens] = useState("");
  const [result, setResult] = useState<PredictResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;

    setLoading(true);
    setError(null);
    setTokens("");
    setResult(null);

    await predictStream(input, {
      onToken: (content) => setTokens((prev) => prev + content),
      onResult: (data) => setResult(data),
      onDone: () => setLoading(false),
      onError: (msg) => {
        setError(msg);
        setLoading(false);
      },
    });
  }

  return (
    <>
      <h1 className="mb-8 text-2xl font-bold">WPP</h1>

      <form onSubmit={handleSubmit} className="mb-8 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. show me skincare products for gen z under 100k"
          className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-gray-900 px-4 py-2 text-sm text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {loading ? "..." : "Submit"}
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {tokens && (
        <div className="mb-4 rounded border border-gray-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold text-gray-500">
            Raw stream
          </h2>
          <pre className="whitespace-pre-wrap text-sm font-mono">{tokens}</pre>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="rounded border border-gray-200 bg-white p-4">
            <h2 className="mb-2 text-sm font-semibold text-gray-500">
              Intent
            </h2>
            <p className="text-lg">{result.intent}</p>
          </div>
          <div className="rounded border border-gray-200 bg-white p-4">
            <h2 className="mb-2 text-sm font-semibold text-gray-500">
              Entities
            </h2>
            <dl className="space-y-1">
              {Object.entries(result.entities).map(([key, value]) =>
                value != null ? (
                  <div key={key} className="flex gap-2 text-sm">
                    <dt className="font-medium text-gray-600">{key}:</dt>
                    <dd>{String(value)}</dd>
                  </div>
                ) : null
              )}
            </dl>
          </div>
        </div>
      )}
    </>
  );
}
