"use client";

import Link from "next/link";
import * as React from "react";

import { LineChart } from "@/app/components/LineChart";
import { PromptInput } from "@/app/components/PromptInput";
import { useRealtimeRefresh } from "@/app/lib/realtime";
import {
  apiJson,
  LiveRunOut,
  LlmDecision,
  ModelPublicOut,
  PricePoint,
  RunOut,
  TimelinePoint,
} from "@/app/lib/v4t";

function fmt(dt: string | null) {
  if (!dt) return "–";
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return dt;
  }
}

function timeLabel(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function runBadge(status: string) {
  if (status === "finished") return "bg-[color:var(--accent)]/10 text-[color:var(--accent)] border border-[color:var(--accent)]/30 drop-shadow-[0_0_8px_var(--accent-glow)]";
  if (status === "running") return "bg-[color:var(--accent-2)]/10 text-[color:var(--accent-2)] border border-[color:var(--accent-2)]/30 drop-shadow-[0_0_8px_var(--accent-2-glow)]";
  if (status === "failed") return "bg-rose-500/10 text-rose-400 border border-rose-500/30 drop-shadow-[0_0_8px_rgba(244,63,94,0.15)]";
  if (status === "cancelled") return "bg-zinc-500/10 text-zinc-400 border border-zinc-500/30";
  return "bg-zinc-500/10 text-zinc-400 border border-zinc-500/30";
}

function decisionTarget(dec: LlmDecision) {
  const v = dec.targets?.[dec.market_id];
  if (v !== undefined) return v;
  const firstKey = dec.targets ? Object.keys(dec.targets)[0] : undefined;
  return firstKey ? dec.targets[firstKey] : "";
}

export default function LivePage() {
  const [liveRun, setLiveRun] = React.useState<RunOut | null>(null);
  const [prices, setPrices] = React.useState<PricePoint[]>([]);
  const [timeline, setTimeline] = React.useState<TimelinePoint[]>([]);
  const [decisions, setDecisions] = React.useState<LlmDecision[]>([]);

  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const [models, setModels] = React.useState<ModelPublicOut[]>([]);

  // Start / restart form (defaults aim for a demo-friendly live loop)
  const [marketId, setMarketId] = React.useState("spot:demo:DEMO");
  const [modelKey, setModelKey] = React.useState("stub");
  const [promptText, setPromptText] = React.useState("");

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

  const [liveSource, setLiveSource] = React.useState<"demo" | "dexscreener">("demo");
  const [chainId, setChainId] = React.useState("solana");
  const [pairId, setPairId] = React.useState("<pairAddress>");
  const [basePrice, setBasePrice] = React.useState(1.0);
  const [forceRestart, setForceRestart] = React.useState(false);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const liveRes = await apiJson<LiveRunOut>("/live/run");

      const r = liveRes.run;
      setLiveRun(r);
      if (!r) {
        setPrices([]);
        setTimeline([]);
        setDecisions([]);
        return;
      }

      const [pricesRes, tlRes, decRes] = await Promise.all([
        apiJson<PricePoint[]>(`/runs/${r.run_id}/prices?limit=600`),
        apiJson<TimelinePoint[]>(`/runs/${r.run_id}/timeline`),
        apiJson<LlmDecision[]>(`/runs/${r.run_id}/decisions?limit=200&offset=0`),
      ]);
      setPrices(pricesRes);
      setTimeline(tlRes);
      setDecisions(decRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  useRealtimeRefresh({
    wsPath: liveRun ? `/runs/${liveRun.run_id}/ws` : "/runs/ws",
    enabled: true,
    pollIntervalMs: 2500,
    messageDebounceMs: liveRun ? 1250 : 250,
    refresh,
  });

  async function onStart(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!promptText.trim()) {
      setError("Prompt text is required");
      return;
    }

    setLoading(true);
    try {
      await apiJson<RunOut>("/live/run", {
        method: "POST",
        body: {
          market_id: marketId,
          model_key: modelKey,
          prompt_text: promptText,
          live_source: liveSource,
          chain_id: liveSource === "dexscreener" ? chainId : null,
          pair_id: liveSource === "dexscreener" ? pairId : null,
          base_price: basePrice,
          force_restart: forceRestart,
        },
      });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onStop() {
    if (!liveRun) return;
    setError(null);
    try {
      await apiJson<{ status: string }>(`/runs/${liveRun.run_id}/stop`, { method: "POST" });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const pricePoints = prices.map((p) => ({ xLabel: timeLabel(p.observed_at), y: p.price }));
  const equityPoints = timeline.map((p) => ({ xLabel: timeLabel(p.observed_at), y: p.equity_quote }));

  return (
    <div className="animate-rise flex flex-col gap-8">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold tracking-widest text-[color:var(--accent)]">
            CURATED GLOBAL RUN • LIVE MODE
          </p>
          <h2 className="mt-2 font-display text-4xl tracking-tight text-white drop-shadow-sm">Live Dashboard</h2>
          <p className="mt-2 text-sm leading-relaxed text-zinc-400">
            Starts a single long-running live job and renders price + equity + decisions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={refresh}
            className="rounded-full border border-white/20 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-white/10 hover:border-white/30 hover:shadow-[0_0_15px_rgba(255,255,255,0.1)]"
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
          {liveRun?.status === "running" ? (
            <button
              type="button"
              onClick={onStop}
              className="rounded-full bg-rose-500/10 border border-rose-500/30 px-5 py-2.5 text-sm font-semibold text-rose-400 transition-all hover:bg-rose-500/20 hover:text-rose-300 hover:shadow-[0_0_15px_rgba(244,63,94,0.2)]"
            >
              Stop Run
            </button>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm font-medium text-rose-200 shadow-[0_0_20px_rgba(244,63,94,0.1)] backdrop-blur-sm">
          {error}
        </div>
      ) : null}

      <section className="animate-rise-1 relative overflow-hidden rounded-3xl border border-[color:var(--border)] bg-white/5 p-6 shadow-lg backdrop-blur-md">
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-[color:var(--accent-2)]/10 blur-3xl" />
        <div className="relative z-10 flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <div className="flex items-center gap-3">
              <div className="font-display text-2xl tracking-tight text-white">Current Live Run</div>
              <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wider shadow-inner ${runBadge(liveRun?.status ?? "pending")}`}>
                {(liveRun?.status ?? "none") === "running" && (
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-current"></span>
                  </span>
                )}
                {liveRun?.status ?? "none"}
              </span>
            </div>
            <div className="mt-3 grid gap-4 text-sm text-zinc-400 md:grid-cols-3">
              <div className="flex flex-col gap-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">run_id</span>
                <span className="font-mono text-white/90">{liveRun?.run_id ?? "–"}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">market</span>
                <span className="font-mono text-[color:var(--accent)]">{liveRun?.market_id ?? "–"}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">started</span>
                <span className="font-mono text-white/90">{fmt(liveRun?.started_at ?? null)}</span>
              </div>
            </div>
          </div>

          {liveRun ? (
            <Link
              href={`/runs/${liveRun.run_id}`}
              className="rounded-full border border-white/20 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-white/10 hover:shadow-[0_0_15px_rgba(255,255,255,0.1)]"
            >
              Open Overview
            </Link>
          ) : null}
        </div>
      </section>

      <section className="animate-rise-2 rounded-3xl border border-[color:var(--border)] bg-white/5 p-6 shadow-lg backdrop-blur-md">
        <h3 className="font-display text-xl tracking-tight text-white mb-6">Start / Restart Live Run</h3>
        <form onSubmit={onStart} className="grid gap-5 md:grid-cols-2">
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

          <label className="grid gap-1.5 text-sm">
            <span className="text-zinc-400 font-medium">live_source</span>
            <div className="relative">
              <select
                value={liveSource}
                onChange={(e) => setLiveSource(e.target.value as "demo" | "dexscreener")}
                className="w-full h-11 appearance-none rounded-xl border border-white/10 bg-black/40 px-4 text-sm text-white focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all"
              >
                <option value="demo">demo (deterministic)</option>
                <option value="dexscreener">dexscreener (polled)</option>
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-zinc-500">
                <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
                  <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                </svg>
              </div>
            </div>
          </label>

          {liveSource === "dexscreener" ? (
            <label className="grid gap-1.5 text-sm">
              <span className="text-zinc-400 font-medium">chain_id + pair_id</span>
              <div className="grid grid-cols-2 gap-3">
                <input
                  value={chainId}
                  onChange={(e) => setChainId(e.target.value)}
                  className="h-11 rounded-xl border border-white/10 bg-black/40 px-4 font-mono text-sm text-white placeholder-zinc-600 focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all"
                />
                <input
                  value={pairId}
                  onChange={(e) => setPairId(e.target.value)}
                  className="h-11 rounded-xl border border-white/10 bg-black/40 px-4 font-mono text-sm text-white placeholder-zinc-600 focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all"
                />
              </div>
            </label>
          ) : (
            <label className="grid gap-1.5 text-sm">
              <span className="text-zinc-400 font-medium">base_price (demo)</span>
              <input
                type="number"
                value={basePrice}
                onChange={(e) => setBasePrice(Number(e.target.value))}
                className="h-11 rounded-xl border border-white/10 bg-black/40 px-4 font-mono text-sm text-white placeholder-zinc-600 focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all"
              />
            </label>
          )}

          <div className="md:col-span-2">
            <PromptInput value={promptText} onChange={setPromptText} />
          </div>

          <div className="md:col-span-2">
            <label className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/40 px-4 py-2 cursor-pointer transition-all hover:bg-white/5">
              <div className="relative flex items-center">
                <input
                  type="checkbox"
                  checked={forceRestart}
                  onChange={(e) => setForceRestart(e.target.checked)}
                  className="peer h-4 w-4 cursor-pointer appearance-none rounded border border-white/20 bg-black checked:border-[color:var(--accent)] checked:bg-[color:var(--accent)] transition-all"
                />
                <svg
                  className="absolute left-[2px] top-[2px] h-3 w-3 pointer-events-none opacity-0 peer-checked:opacity-100 text-black"
                  viewBox="0 0 14 14"
                  fill="none"
                >
                  <path
                    d="M3 8L6 11L11 3.5"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    stroke="currentColor"
                  />
                </svg>
              </div>
              <span className="text-white font-medium text-sm select-none">force_restart</span>
            </label>
          </div>

          <div className="md:col-span-2 flex items-center justify-end pt-4">
            <button
              type="submit"
              className="rounded-full bg-white px-8 py-3 text-sm font-bold text-black transition-all hover:bg-zinc-200 hover:shadow-[0_0_20px_rgba(255,255,255,0.2)] disabled:opacity-50"
            >
              Start Live Run
            </button>
          </div>
        </form>
      </section>

      <section className="animate-rise-2 grid gap-4 lg:grid-cols-2">
        <LineChart
          title="Price"
          ariaLabel="Price line chart"
          points={pricePoints}
          strokeFrom="rgba(249,115,22,0.88)"
          strokeTo="rgba(15,118,110,0.92)"
        />
        <LineChart title="Equity" ariaLabel="Equity line chart" points={equityPoints} />
      </section>

      <section className="animate-rise-3 overflow-hidden rounded-3xl border border-[color:var(--border)] bg-white/5 shadow-lg backdrop-blur-md">
        <div className="flex items-center justify-between border-b border-white/10 bg-white/5 px-6 py-5">
          <h3 className="font-display text-xl tracking-tight text-white flex items-center gap-2">
            <svg className="w-5 h-5 text-[color:var(--accent-2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Decisions
          </h3>
          <div className="rounded-full bg-white/10 px-3 py-1.5 text-xs font-medium text-white shadow-inner">
            {decisions.length} loaded
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-black/20 text-xs uppercase tracking-wider text-zinc-400">
              <tr>
                <th className="px-6 py-4 font-semibold">Tick</th>
                <th className="px-6 py-4 font-semibold">Accepted</th>
                <th className="px-6 py-4 font-semibold">Target</th>
                <th className="px-6 py-4 font-semibold">Conf</th>
                <th className="px-6 py-4 font-semibold text-right" style={{ minWidth: 250 }}>Reason / Rationale</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {decisions.map((d, i) => (
                <tr key={d.llm_call_id ?? `${d.tick_time}-${i}`} className="align-top transition-colors hover:bg-white/5">
                  <td className="px-6 py-4 font-mono text-xs text-zinc-300">
                    {fmt(d.tick_time)}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={
                        d.accepted
                          ? "inline-flex items-center rounded-full bg-[color:var(--accent)]/10 border border-[color:var(--accent)]/30 px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wider text-[color:var(--accent)] drop-shadow-[0_0_8px_var(--accent-glow)]"
                          : "inline-flex items-center rounded-full bg-rose-500/10 border border-rose-500/30 px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wider text-rose-400 drop-shadow-[0_0_8px_rgba(244,63,94,0.15)]"
                      }
                    >
                      {d.accepted ? "yes" : "no"}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-mono text-xs text-white">
                    {decisionTarget(d)}
                  </td>
                  <td className="px-6 py-4 font-mono text-xs text-zinc-300">
                    {d.confidence ?? ""}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {d.reject_reason ? (
                      <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-rose-400 bg-rose-500/10 px-2 py-1 rounded">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        {d.reject_reason}
                      </div>
                    ) : null}
                    {d.rationale ? (
                      <div className="mt-2 text-xs leading-relaxed text-zinc-400 line-clamp-2 hover:line-clamp-none transition-all">{d.rationale}</div>
                    ) : null}
                  </td>
                </tr>
              ))}
              {decisions.length === 0 ? (
                <tr>
                  <td className="px-6 py-12 text-center text-sm text-zinc-500" colSpan={5}>
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <svg className="h-10 w-10 text-zinc-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p>No decisions yet. Start a live run relative to your dataset.</p>
                    </div>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
