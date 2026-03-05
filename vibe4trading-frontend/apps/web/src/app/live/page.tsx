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
  if (status === "finished") return "border border-[#2d7f4c] bg-[#d6f0dc] text-[#131313]";
  if (status === "running") return "border border-[#3351a6] bg-[#dfe8ff] text-[#131313]";
  if (status === "failed") return "border border-[#c0392b] bg-[#f9e5e5] text-[#c0392b]";
  return "border border-[#555] bg-[#f0f0f0] text-[#555]";
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
    <main className="live-page-main animate-rise flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-1">LIVE DASHBOARD</h1>
          <p className="text-lg text-[#4f4f4f]">
            Starts a single long-running live job and renders price + equity + decisions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={refresh}
            className="newrun-action-btn ghost"
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
          {liveRun?.status === "running" ? (
            <button
              type="button"
              onClick={onStop}
              className="newrun-action-btn"
              style={{ background: "#f9e5e5", color: "#c0392b", borderColor: "#c0392b" }}
            >
              Stop Run
            </button>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="bg-[#f9e5e5] border-2 border-[#c0392b] text-[#c0392b] p-3 text-lg">
          {error}
        </div>
      ) : null}

      <section className="block">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="text-2xl font-bold">Current Live Run</div>
              <span className={`px-2 py-0.5 text-sm uppercase tracking-wider ${runBadge(liveRun?.status ?? "pending")}`}>
                {(liveRun?.status ?? "none") === "running" && (
                  <span className="inline-block w-2 h-2 mr-1 rounded-full bg-current animate-pulse"></span>
                )}
                {liveRun?.status ?? "none"}
              </span>
            </div>
            <div className="grid gap-4 text-lg md:grid-cols-3">
              <div className="flex flex-col">
                <span className="text-sm font-bold text-[#666]">RUN_ID</span>
                <span>{liveRun?.run_id ?? "–"}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-bold text-[#666]">MARKET</span>
                <span className="text-[var(--blue)] font-bold">{liveRun?.market_id ?? "–"}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-bold text-[#666]">STARTED</span>
                <span>{fmt(liveRun?.started_at ?? null)}</span>
              </div>
            </div>
          </div>

          {liveRun ? (
            <Link
              href={`/runs/${liveRun.run_id}`}
              className="newrun-action-btn"
            >
              Open Overview
            </Link>
          ) : null}
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <section className="block lg:col-span-1">
          <h3 className="text-2xl font-bold mb-4">Start / Restart Live Run</h3>
          <form onSubmit={onStart} className="newrun-form">
            <label className="newrun-field">
              <span>market_id</span>
              <input
                value={marketId}
                onChange={(e) => setMarketId(e.target.value)}
                required
              />
            </label>
            <label className="newrun-field">
              <span>model_key</span>
              <select
                value={modelKey}
                onChange={(e) => setModelKey(e.target.value)}
                required
              >
                {models.map((m) => (
                  <option key={m.model_key} value={m.model_key}>
                    {m.label ? `${m.label} (${m.model_key})` : m.model_key}
                  </option>
                ))}
              </select>
            </label>

            <label className="newrun-field">
              <span>live_source</span>
              <select
                value={liveSource}
                onChange={(e) => setLiveSource(e.target.value as "demo" | "dexscreener")}
              >
                <option value="demo">demo (deterministic)</option>
                <option value="dexscreener">dexscreener (polled)</option>
              </select>
            </label>

            {liveSource === "dexscreener" ? (
              <label className="newrun-field">
                <span>chain_id / pair_id</span>
                <div className="flex gap-2">
                  <input
                    value={chainId}
                    onChange={(e) => setChainId(e.target.value)}
                    style={{ width: "50%" }}
                  />
                  <input
                    value={pairId}
                    onChange={(e) => setPairId(e.target.value)}
                    style={{ width: "50%" }}
                  />
                </div>
              </label>
            ) : (
              <label className="newrun-field">
                <span>base_price (demo)</span>
                <input
                  type="number"
                  value={basePrice}
                  onChange={(e) => setBasePrice(Number(e.target.value))}
                />
              </label>
            )}

            <div className="newrun-field">
              <span>prompt</span>
              <PromptInput value={promptText} onChange={setPromptText} />
            </div>

            <label className="flex items-center gap-2 mt-2 cursor-pointer border-2 border-[#404040] p-2 bg-[#f9f9f9]">
              <input
                type="checkbox"
                checked={forceRestart}
                onChange={(e) => setForceRestart(e.target.checked)}
                className="w-5 h-5"
              />
              <span className="text-lg">force_restart</span>
            </label>

            <div className="flex justify-end mt-2">
              <button
                type="submit"
                className="newrun-action-btn"
              >
                Start Live Run
              </button>
            </div>
          </form>
        </section>

        <section className="lg:col-span-2 flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-64">
            <div className="block h-full">
              <LineChart
                title="Price"
                ariaLabel="Price line chart"
                points={pricePoints}
                strokeFrom="rgba(249,115,22,0.88)"
                strokeTo="rgba(15,118,110,0.92)"
              />
            </div>
            <div className="block h-full">
              <LineChart title="Equity" ariaLabel="Equity line chart" points={equityPoints} />
            </div>
          </div>

          <section className="block flex-1 overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-2xl font-bold">
                Decisions
              </h3>
              <div className="text-sm text-[#555]">
                {decisions.length} loaded
              </div>
            </div>

            <div className="overflow-y-auto border-2 border-[#4a4a4a] bg-[#fdfdfd]" style={{ maxHeight: "300px" }}>
              <table className="w-full text-left">
                <thead className="bg-[#e5e5e5] text-sm uppercase sticky top-0 border-b-2 border-[#4a4a4a]">
                  <tr>
                    <th className="px-3 py-2 font-semibold border-r border-[#c2c2c2]">Tick</th>
                    <th className="px-3 py-2 font-semibold border-r border-[#c2c2c2]">Accepted</th>
                    <th className="px-3 py-2 font-semibold border-r border-[#c2c2c2]">Target</th>
                    <th className="px-3 py-2 font-bold text-right" style={{ minWidth: 200 }}>Reason / Rationale</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {decisions.map((d, i) => (
                    <tr key={d.llm_call_id ?? `${d.tick_time}-${i}`} className="border-b border-[#c2c2c2] hover:bg-[#ebf0fc]">
                      <td className="px-3 py-2 border-r border-[#c2c2c2]">
                        {fmt(d.tick_time)}
                      </td>
                      <td className="px-3 py-2 border-r border-[#c2c2c2]">
                        <span className={`px-2 py-0.5 text-xs font-bold ${d.accepted ? 'bg-[#d6f0dc] text-[#1d7e4b] border border-[#2d7f4c]' : 'bg-[#f9e5e5] text-[#c0392b] border border-[#c0392b]'}`}>
                          {d.accepted ? "YES" : "NO"}
                        </span>
                      </td>
                      <td className="px-3 py-2 border-r border-[#c2c2c2] font-mono">
                        {decisionTarget(d)}
                      </td>
                      <td className="px-3 py-2">
                        {d.reject_reason ? (
                          <div className="text-xs font-bold text-[#c0392b] mb-1">
                            [{d.reject_reason}]
                          </div>
                        ) : null}
                        {d.rationale ? (
                          <div className="text-xs text-[#444] line-clamp-2 hover:line-clamp-none" title={d.rationale}>{d.rationale}</div>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                  {decisions.length === 0 ? (
                    <tr>
                      <td className="px-3 py-8 text-center text-[#666]" colSpan={4}>
                        No decisions yet. Start a live run.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>
        </section>
      </div>

    </main>
  );
}
