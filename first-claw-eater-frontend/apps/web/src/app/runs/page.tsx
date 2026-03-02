"use client";

import Link from "next/link";
import * as React from "react";

import {
  apiJson,
  DatasetOut,
  PromptTemplateOut,
  RunOut,
} from "@/app/lib/fce";

function fmt(dt: string | null) {
  if (!dt) return "–";
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return dt;
  }
}

function runBadge(status: string) {
  if (status === "finished") return "bg-emerald-100 text-emerald-900";
  if (status === "running") return "bg-amber-100 text-amber-900";
  if (status === "failed") return "bg-rose-100 text-rose-900";
  if (status === "cancelled") return "bg-zinc-200 text-zinc-900";
  return "bg-zinc-200 text-zinc-900";
}

export default function RunsPage() {
  const [runs, setRuns] = React.useState<RunOut[]>([]);
  const [datasets, setDatasets] = React.useState<DatasetOut[]>([]);
  const [templates, setTemplates] = React.useState<PromptTemplateOut[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Run form
  const [marketId, setMarketId] = React.useState("spot:demo:DEMO");
  const [modelKey, setModelKey] = React.useState("stub");
  const [spotDatasetId, setSpotDatasetId] = React.useState<string>("");
  const [sentDatasetId, setSentDatasetId] = React.useState<string>("");
  const [promptTemplateId, setPromptTemplateId] = React.useState<string>("");
  const [promptVars, setPromptVars] = React.useState(
    JSON.stringify({ risk_style: "balanced" }, null, 2),
  );

  const [baseIntervalSeconds, setBaseIntervalSeconds] = React.useState(3600);
  const [minIntervalSeconds, setMinIntervalSeconds] = React.useState(60);
  const [priceTickSeconds, setPriceTickSeconds] = React.useState(60);
  const [lookbackBars, setLookbackBars] = React.useState(24);
  const [timeframe, setTimeframe] = React.useState("1h");
  const [timeOffsetSeconds, setTimeOffsetSeconds] = React.useState(0);
  const [feeBps, setFeeBps] = React.useState(10);
  const [initialEquityQuote, setInitialEquityQuote] = React.useState(1000);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [runsRes, datasetsRes, templatesRes] = await Promise.all([
        apiJson<RunOut[]>("/runs"),
        apiJson<DatasetOut[]>("/datasets"),
        apiJson<PromptTemplateOut[]>("/prompt_templates").catch(() => []),
      ]);
      setRuns(runsRes);
      setDatasets(datasetsRes);
      setTemplates(templatesRes);

      // Fill defaults when first data arrives.
      const readySpot = datasetsRes.find(
        (d) => d.category === "spot" && d.status === "ready",
      );
      const readySent = datasetsRes.find(
        (d) => d.category === "sentiment" && d.status === "ready",
      );
      setSpotDatasetId((prev) => prev || readySpot?.dataset_id || "");
      setSentDatasetId((prev) => prev || readySent?.dataset_id || "");
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
    const t = setInterval(refresh, 2500);
    return () => clearInterval(t);
  }, [refresh]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    let prompt_vars: Record<string, unknown> = {};
    try {
      prompt_vars = promptVars.trim()
        ? (JSON.parse(promptVars) as Record<string, unknown>)
        : {};
    } catch {
      setError("prompt_vars must be valid JSON (or empty)");
      return;
    }

    if (!spotDatasetId || !sentDatasetId) {
      setError("Pick a ready spot dataset and a ready sentiment dataset");
      return;
    }

    setLoading(true);
    try {
        await apiJson<RunOut>("/runs", {
          method: "POST",
          body: {
          market_id: marketId,
          model_key: modelKey,
          spot_dataset_id: spotDatasetId,
          sentiment_dataset_id: sentDatasetId,
          prompt_template_id: promptTemplateId || null,
          prompt_vars,
          base_interval_seconds: baseIntervalSeconds,
          min_interval_seconds: minIntervalSeconds,
          price_tick_seconds: priceTickSeconds,
            lookback_bars: lookbackBars,
            timeframe,
            time_offset_seconds: timeOffsetSeconds,
            fee_bps: feeBps,
            initial_equity_quote: initialEquityQuote,
          },
        });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
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

  const readySpot = datasets.filter((d) => d.category === "spot" && d.status === "ready");
  const readySent = datasets.filter(
    (d) => d.category === "sentiment" && d.status === "ready",
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-3xl tracking-tight">Runs</h2>
          <p className="mt-1 text-sm leading-6 text-black/60">
            Replay execution is queued to the backend worker. This page polls.
          </p>
        </div>

        <button
          type="button"
          onClick={refresh}
          className="rounded-full border border-black/15 bg-white/60 px-4 py-2 text-sm font-medium text-black/80 hover:bg-white"
        >
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      <section className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-6 shadow-[var(--shadow)]">
        <h3 className="font-display text-xl tracking-tight">Create Run</h3>
        <form onSubmit={onCreate} className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="grid gap-1 text-sm">
            <span className="text-black/65">market_id</span>
            <input
              value={marketId}
              onChange={(e) => setMarketId(e.target.value)}
              className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              required
            />
          </label>

          <label className="grid gap-1 text-sm">
            <span className="text-black/65">model_key</span>
            <input
              value={modelKey}
              onChange={(e) => setModelKey(e.target.value)}
              className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              required
            />
          </label>

          <label className="grid gap-1 text-sm">
            <span className="text-black/65">spot_dataset_id</span>
            <select
              value={spotDatasetId}
              onChange={(e) => setSpotDatasetId(e.target.value)}
              className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              required
            >
              <option value="" disabled>
                Select…
              </option>
              {readySpot.map((d) => (
                <option key={d.dataset_id} value={d.dataset_id}>
                  {d.dataset_id.slice(0, 8)}… ({d.source})
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-1 text-sm">
            <span className="text-black/65">sentiment_dataset_id</span>
            <select
              value={sentDatasetId}
              onChange={(e) => setSentDatasetId(e.target.value)}
              className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              required
            >
              <option value="" disabled>
                Select…
              </option>
              {readySent.map((d) => (
                <option key={d.dataset_id} value={d.dataset_id}>
                  {d.dataset_id.slice(0, 8)}… ({d.source})
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-1 text-sm md:col-span-2">
            <span className="text-black/65">prompt_template_id (optional)</span>
            <select
              value={promptTemplateId}
              onChange={(e) => setPromptTemplateId(e.target.value)}
              className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
            >
              <option value="">(default built-in)</option>
              {templates.map((t) => (
                <option key={t.template_id} value={t.template_id}>
                  {t.name} — {t.template_id.slice(0, 8)}…
                </option>
              ))}
            </select>
          </label>

          <label className="md:col-span-2 grid gap-1 text-sm">
            <span className="text-black/65">prompt_vars (JSON)</span>
            <textarea
              value={promptVars}
              onChange={(e) => setPromptVars(e.target.value)}
              rows={4}
              className="rounded-2xl border border-black/15 bg-white/70 p-3 font-mono text-xs"
            />
          </label>

          <div className="grid gap-3 md:col-span-2 md:grid-cols-4">
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">base_interval_seconds</span>
              <input
                type="number"
                value={baseIntervalSeconds}
                onChange={(e) => setBaseIntervalSeconds(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">min_interval_seconds</span>
              <input
                type="number"
                value={minIntervalSeconds}
                onChange={(e) => setMinIntervalSeconds(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">price_tick_seconds</span>
              <input
                type="number"
                value={priceTickSeconds}
                onChange={(e) => setPriceTickSeconds(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">lookback_bars</span>
              <input
                type="number"
                value={lookbackBars}
                onChange={(e) => setLookbackBars(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
          </div>

          <div className="grid gap-3 md:col-span-2 md:grid-cols-3">
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">timeframe</span>
              <input
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">time_offset_seconds</span>
              <input
                type="number"
                value={timeOffsetSeconds}
                onChange={(e) => setTimeOffsetSeconds(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">fee_bps</span>
              <input
                type="number"
                value={feeBps}
                onChange={(e) => setFeeBps(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">initial_equity_quote</span>
              <input
                type="number"
                value={initialEquityQuote}
                onChange={(e) => setInitialEquityQuote(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
          </div>

          <div className="md:col-span-2 flex items-center justify-end gap-3">
            <button
              type="submit"
              className="rounded-full bg-[color:var(--ink)] px-5 py-2.5 text-sm font-medium text-[color:var(--surface)] hover:bg-black"
            >
              Create + Enqueue Run
            </button>
          </div>
        </form>

        {error ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900">
            {error}
          </div>
        ) : null}
      </section>

      <section className="grid gap-4">
        {runs.map((r) => (
          <div
            key={r.run_id}
            className="rounded-3xl border border-black/10 bg-white/60 p-5 shadow-[var(--shadow)]"
          >
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
              <div>
                <div className="flex items-center gap-3">
                  <Link
                    href={`/runs/${r.run_id}`}
                    className="font-display text-xl tracking-tight hover:underline"
                  >
                    {r.market_id}
                  </Link>
                  <span
                    className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${runBadge(r.status)}`}
                  >
                    {r.status}
                  </span>
                </div>
                <div className="mt-2 grid gap-1 text-xs text-black/60 md:grid-cols-3">
                  <div>
                    <span className="text-black/40">run_id</span>{" "}
                    <span className="font-mono">{r.run_id}</span>
                  </div>
                  <div>
                    <span className="text-black/40">model</span>{" "}
                    <span className="font-mono">{r.model_key}</span>
                  </div>
                  <div>
                    <span className="text-black/40">started</span>{" "}
                    <span className="font-mono">{fmt(r.started_at)}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Link
                  href={`/runs/${r.run_id}`}
                  className="rounded-full border border-black/15 bg-white/60 px-4 py-2 text-sm font-medium text-black/80 hover:bg-white"
                >
                  Open
                </Link>
                {r.status === "running" ? (
                  <button
                    type="button"
                    onClick={() => onStop(r.run_id)}
                    className="rounded-full bg-[color:var(--accent-2)] px-4 py-2 text-sm font-medium text-white hover:brightness-95"
                  >
                    Stop
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        ))}

        {runs.length === 0 ? (
          <div className="rounded-3xl border border-black/10 bg-white/60 p-10 text-sm text-black/60 shadow-[var(--shadow)]">
            No runs yet.
          </div>
        ) : null}
      </section>
    </div>
  );
}
