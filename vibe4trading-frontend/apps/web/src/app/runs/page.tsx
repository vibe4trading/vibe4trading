"use client";

import Link from "next/link";
import * as React from "react";

import { PromptInput } from "@/app/components/PromptInput";
import { useRealtimeRefresh } from "@/app/lib/realtime";
import { apiJson, ModelPublicOut, RunOut } from "@/app/lib/v4t";

function fmt(dt: string | null) {
  if (!dt) return "–";
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return dt;
  }
}

function runBadge(status: string) {
  if (status === "finished")
    return "bg-[color:var(--accent)]/10 text-[color:var(--accent)] border border-[color:var(--accent)]/30 drop-shadow-[0_0_8px_var(--accent-glow)]";
  if (status === "running")
    return "bg-[color:var(--accent-2)]/10 text-[color:var(--accent-2)] border border-[color:var(--accent-2)]/30 drop-shadow-[0_0_8px_var(--accent-2-glow)]";
  if (status === "failed")
    return "bg-rose-500/10 text-rose-400 border border-rose-500/30 drop-shadow-[0_0_8px_rgba(244,63,94,0.15)]";
  if (status === "cancelled") return "bg-zinc-500/10 text-zinc-400 border border-zinc-500/30";
  return "bg-zinc-500/10 text-zinc-400 border border-zinc-500/30";
}

export default function RunsPage() {
  const [runs, setRuns] = React.useState<RunOut[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [creating, setCreating] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const [models, setModels] = React.useState<ModelPublicOut[]>([]);

  const [marketId, setMarketId] = React.useState("spot:demo:DEMO");
  const [modelKey, setModelKey] = React.useState("stub");
  const [promptText, setPromptText] = React.useState("");

  const marketDatasetId = process.env.NEXT_PUBLIC_V4T_MARKET_DATASET_ID ?? "";
  const sentimentDatasetId = process.env.NEXT_PUBLIC_V4T_SENTIMENT_DATASET_ID ?? "";

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const runsRes = await apiJson<RunOut[]>("/runs");
      setRuns(runsRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  React.useEffect(() => {
    apiJson<ModelPublicOut[]>("/models")
      .then((rows) => {
        setModels(rows);
        setModelKey((prev) => {
          if (rows.some((m) => m.model_key === prev)) return prev;
          return rows[0]?.model_key ?? "stub";
        });
      })
      .catch((e) => {
        setError(`Failed to load models: ${e instanceof Error ? e.message : String(e)}`);
        setModels([{ model_key: "stub", label: "Stub" }]);
        setModelKey("stub");
      });
  }, []);

  useRealtimeRefresh({
    wsPath: "/runs/ws",
    enabled: true,
    pollIntervalMs: 2500,
    refresh,
  });

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!promptText.trim()) {
      setError("Prompt text is required");
      return;
    }

    if (!marketDatasetId || !sentimentDatasetId) {
      setError(
        "Dataset IDs are not configured. Set NEXT_PUBLIC_V4T_MARKET_DATASET_ID and NEXT_PUBLIC_V4T_SENTIMENT_DATASET_ID.",
      );
      return;
    }

    setCreating(true);
    try {
      await apiJson<RunOut>("/runs", {
        method: "POST",
        body: {
          market_id: marketId,
          model_key: modelKey,
          market_dataset_id: marketDatasetId,
          sentiment_dataset_id: sentimentDatasetId,
          prompt_text: promptText,
        },
      });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCreating(false);
    }
  }

  async function onStop(runId: string) {
    setError(null);
    try {
      await apiJson<{ status: string }>(`/runs/${runId}/stop`, { method: "POST" });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="flex flex-col gap-8 animate-rise">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold tracking-widest text-[color:var(--accent)]">
            REPLAY EXECUTION
          </p>
           <h2 className="mt-2 font-display text-4xl tracking-tight text-white drop-shadow-sm">Runs</h2>
           <p className="mt-2 text-sm leading-relaxed text-zinc-400">
             Replay execution is queued to the backend worker. Updates stream via WebSocket (poll fallback).
           </p>
         </div>

        <button
          type="button"
          onClick={refresh}
          className="rounded-full border border-white/20 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-white/10 hover:border-white/30 hover:shadow-[0_0_15px_rgba(255,255,255,0.1)]"
        >
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm font-medium text-rose-200 shadow-[0_0_20px_rgba(244,63,94,0.1)] backdrop-blur-sm">
          {error}
        </div>
      ) : null}

      <section className="animate-rise-1 rounded-3xl border border-[color:var(--border)] bg-white/5 p-6 shadow-lg backdrop-blur-md">
        <h3 className="font-display text-xl tracking-tight text-white mb-6">Create Run</h3>
        <form onSubmit={onCreate} className="grid gap-5 md:grid-cols-2">
          <label className="grid gap-1.5 text-sm">
            <span className="text-zinc-400 font-medium">market_id</span>
            <input
              value={marketId}
              onChange={(e) => setMarketId(e.target.value)}
              className="h-11 rounded-xl border border-white/10 bg-black/40 px-4 font-mono text-sm text-white placeholder-zinc-600 focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all"
              required
            />
          </label>

          <label className="grid gap-1.5 text-sm">
            <span className="text-zinc-400 font-medium">model_key</span>
            <div className="relative">
              <select
                value={modelKey}
                onChange={(e) => setModelKey(e.target.value)}
                className="w-full h-11 appearance-none rounded-xl border border-white/10 bg-black/40 px-4 font-mono text-xs text-white focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all"
                required
              >
                {models.map((m) => (
                  <option key={m.model_key} value={m.model_key}>
                    {m.label ? `${m.label} (${m.model_key})` : m.model_key}
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-zinc-500">
                <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
                  <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                </svg>
              </div>
            </div>
          </label>

          <div className="md:col-span-2 rounded-2xl border border-white/10 bg-black/30 p-4 text-sm text-zinc-300">
            Datasets are injected via the API for MVP. Configure dataset IDs via
            <span className="font-mono text-xs text-white"> NEXT_PUBLIC_V4T_MARKET_DATASET_ID</span> and
            <span className="font-mono text-xs text-white"> NEXT_PUBLIC_V4T_SENTIMENT_DATASET_ID</span>.
          </div>

          <div className="md:col-span-2">
            <PromptInput value={promptText} onChange={setPromptText} />
          </div>

          <div className="md:col-span-2 flex items-center justify-end pt-4">
            <button
              type="submit"
              className="rounded-full bg-white px-8 py-3 text-sm font-bold text-black transition-all hover:bg-zinc-200 hover:shadow-[0_0_20px_rgba(255,255,255,0.2)] disabled:opacity-50"
              disabled={creating}
            >
              {creating ? "Creating…" : "Create + Enqueue Run"}
            </button>
          </div>
        </form>
      </section>

      <section className="animate-rise-2 grid gap-4">
        {runs.map((r) => (
          <div
            key={r.run_id}
            className="relative overflow-hidden rounded-3xl border border-[color:var(--border)] bg-white/5 p-6 shadow-lg backdrop-blur-md transition-all hover:border-white/15"
          >
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
              <div>
                <div className="flex items-center gap-3">
                  <Link
                    href={`/runs/${r.run_id}`}
                    className="font-display text-xl tracking-tight text-white hover:text-[color:var(--accent)] transition-colors"
                  >
                    {r.market_id}
                  </Link>
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wider ${runBadge(r.status)}`}
                  >
                    {r.status === "running" && (
                      <span className="relative flex h-1.5 w-1.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-current"></span>
                      </span>
                    )}
                    {r.status}
                  </span>
                </div>
                <div className="mt-3 grid gap-4 text-sm text-zinc-400 md:grid-cols-3">
                  <div className="flex flex-col gap-1">
                    <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">run_id</span>
                    <span className="font-mono text-white/90">{r.run_id}</span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">model</span>
                    <span className="font-mono text-[color:var(--accent-2)]">{r.model_key}</span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">started</span>
                    <span className="font-mono text-white/90">{fmt(r.started_at)}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Link
                  href={`/runs/${r.run_id}`}
                  className="rounded-full border border-white/20 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-white/10 hover:shadow-[0_0_15px_rgba(255,255,255,0.1)]"
                >
                  Open
                </Link>
                {r.status === "running" ? (
                  <button
                    type="button"
                    onClick={() => onStop(r.run_id)}
                    className="rounded-full bg-rose-500/10 border border-rose-500/30 px-5 py-2.5 text-sm font-semibold text-rose-400 transition-all hover:bg-rose-500/20 hover:text-rose-300 hover:shadow-[0_0_15px_rgba(244,63,94,0.2)]"
                  >
                    Stop
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        ))}

        {runs.length === 0 ? (
          <div className="rounded-3xl border border-[color:var(--border)] bg-white/5 p-12 shadow-lg backdrop-blur-md">
            <div className="flex flex-col items-center justify-center space-y-3">
              <svg className="h-10 w-10 text-zinc-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <p className="text-sm text-zinc-500">No runs yet. Create one above.</p>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
