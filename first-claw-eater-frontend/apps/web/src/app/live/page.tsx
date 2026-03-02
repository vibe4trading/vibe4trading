"use client";

import Link from "next/link";
import * as React from "react";

import { LineChart } from "@/app/components/LineChart";
import {
  apiJson,
  LiveRunOut,
  LlmDecision,
  PricePoint,
  PromptTemplateOut,
  RunOut,
  TimelinePoint,
} from "@/app/lib/fce";

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
  if (status === "finished") return "bg-emerald-100 text-emerald-900";
  if (status === "running") return "bg-amber-100 text-amber-900";
  if (status === "failed") return "bg-rose-100 text-rose-900";
  if (status === "cancelled") return "bg-zinc-200 text-zinc-900";
  return "bg-zinc-200 text-zinc-900";
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
  const [templates, setTemplates] = React.useState<PromptTemplateOut[]>([]);

  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Start / restart form (defaults aim for a demo-friendly live loop)
  const [marketId, setMarketId] = React.useState("spot:demo:DEMO");
  const [modelKey, setModelKey] = React.useState("stub");
  const [promptTemplateId, setPromptTemplateId] = React.useState<string>("");
  const [promptVars, setPromptVars] = React.useState(
    JSON.stringify({ risk_style: "balanced" }, null, 2),
  );

  const [liveSource, setLiveSource] = React.useState<"demo" | "dexscreener">("demo");
  const [chainId, setChainId] = React.useState("solana");
  const [pairId, setPairId] = React.useState("<pairAddress>");
  const [basePrice, setBasePrice] = React.useState(1.0);

  const [baseIntervalSeconds, setBaseIntervalSeconds] = React.useState(60);
  const [minIntervalSeconds, setMinIntervalSeconds] = React.useState(30);
  const [priceTickSeconds, setPriceTickSeconds] = React.useState(5);
  const [lookbackBars, setLookbackBars] = React.useState(60);
  const [timeframe, setTimeframe] = React.useState("1m");
  const [timeOffsetSeconds, setTimeOffsetSeconds] = React.useState(0);
  const [feeBps, setFeeBps] = React.useState(10);
  const [initialEquityQuote, setInitialEquityQuote] = React.useState(1000);
  const [forceRestart, setForceRestart] = React.useState(false);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [liveRes, templatesRes] = await Promise.all([
        apiJson<LiveRunOut>("/live/run"),
        apiJson<PromptTemplateOut[]>("/prompt_templates").catch(() => []),
      ]);
      setTemplates(templatesRes);

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

  React.useEffect(() => {
    const t = setInterval(refresh, 2500);
    return () => clearInterval(t);
  }, [refresh]);

  async function onStart(e: React.FormEvent) {
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

    setLoading(true);
    try {
      await apiJson<RunOut>("/live/run", {
        method: "POST",
        body: {
          market_id: marketId,
          model_key: modelKey,
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
    <div className="animate-rise flex flex-col gap-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-medium tracking-widest text-black/55">
            CURATED GLOBAL RUN • LIVE MODE
          </p>
          <h2 className="mt-2 font-display text-3xl tracking-tight">Live Dashboard</h2>
          <p className="mt-1 text-sm leading-6 text-black/60">
            Starts a single long-running live job and renders price + equity + decisions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={refresh}
            className="rounded-full border border-black/15 bg-white/60 px-4 py-2 text-sm font-medium text-black/80 hover:bg-white"
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
          {liveRun?.status === "running" ? (
            <button
              type="button"
              onClick={onStop}
              className="rounded-full bg-[color:var(--accent-2)] px-4 py-2 text-sm font-medium text-white hover:brightness-95"
            >
              Stop
            </button>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900">
          {error}
        </div>
      ) : null}

      <section className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-6 shadow-[var(--shadow)]">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <div className="flex items-center gap-3">
              <div className="font-display text-xl tracking-tight">Current Live Run</div>
              <span
                className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${runBadge(liveRun?.status ?? "pending")}`}
              >
                {liveRun?.status ?? "none"}
              </span>
            </div>
            <div className="mt-2 grid gap-1 text-xs text-black/60 md:grid-cols-3">
              <div>
                <span className="text-black/40">run_id</span>{" "}
                <span className="font-mono">{liveRun?.run_id ?? "–"}</span>
              </div>
              <div>
                <span className="text-black/40">market</span>{" "}
                <span className="font-mono">{liveRun?.market_id ?? "–"}</span>
              </div>
              <div>
                <span className="text-black/40">started</span>{" "}
                <span className="font-mono">{fmt(liveRun?.started_at ?? null)}</span>
              </div>
            </div>
          </div>

          {liveRun ? (
            <Link
              href={`/runs/${liveRun.run_id}`}
              className="rounded-full border border-black/15 bg-white/60 px-4 py-2 text-sm font-medium text-black/80 hover:bg-white"
            >
              Open As Run
            </Link>
          ) : null}
        </div>
      </section>

      <section className="rounded-3xl border border-black/10 bg-white/60 p-6 shadow-[var(--shadow)]">
        <h3 className="font-display text-xl tracking-tight">Start / Restart Live Run</h3>
        <form onSubmit={onStart} className="mt-4 grid gap-4 md:grid-cols-2">
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
            <span className="text-black/65">live_source</span>
            <select
              value={liveSource}
              onChange={(e) => setLiveSource(e.target.value as "demo" | "dexscreener")}
              className="h-10 rounded-xl border border-black/15 bg-white/70 px-3"
            >
              <option value="demo">demo (deterministic)</option>
              <option value="dexscreener">dexscreener (polled)</option>
            </select>
          </label>

          {liveSource === "dexscreener" ? (
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">chain_id + pair_id</span>
              <div className="grid grid-cols-2 gap-2">
                <input
                  value={chainId}
                  onChange={(e) => setChainId(e.target.value)}
                  className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
                />
                <input
                  value={pairId}
                  onChange={(e) => setPairId(e.target.value)}
                  className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
                />
              </div>
            </label>
          ) : (
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">base_price (demo)</span>
              <input
                type="number"
                value={basePrice}
                onChange={(e) => setBasePrice(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
          )}

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

          <div className="grid gap-3 md:col-span-2 md:grid-cols-6">
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">base_interval</span>
              <input
                type="number"
                value={baseIntervalSeconds}
                onChange={(e) => setBaseIntervalSeconds(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">min_interval</span>
              <input
                type="number"
                value={minIntervalSeconds}
                onChange={(e) => setMinIntervalSeconds(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">price_tick</span>
              <input
                type="number"
                value={priceTickSeconds}
                onChange={(e) => setPriceTickSeconds(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">lookback</span>
              <input
                type="number"
                value={lookbackBars}
                onChange={(e) => setLookbackBars(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">timeframe</span>
              <input
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="text-black/65">time_offset</span>
              <input
                type="number"
                value={timeOffsetSeconds}
                onChange={(e) => setTimeOffsetSeconds(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
          </div>

          <div className="grid gap-3 md:col-span-2 md:grid-cols-3">
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
              <span className="text-black/65">initial_equity</span>
              <input
                type="number"
                value={initialEquityQuote}
                onChange={(e) => setInitialEquityQuote(Number(e.target.value))}
                className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              />
            </label>
            <label className="flex items-center gap-2 rounded-xl border border-black/10 bg-white/50 px-3 py-2 text-sm">
              <input
                type="checkbox"
                checked={forceRestart}
                onChange={(e) => setForceRestart(e.target.checked)}
              />
              <span className="text-black/75">force_restart</span>
            </label>
          </div>

          <div className="md:col-span-2 flex items-center justify-end gap-3">
            <button
              type="submit"
              className="rounded-full bg-[color:var(--ink)] px-5 py-2.5 text-sm font-medium text-[color:var(--surface)] hover:bg-black"
            >
              Start Live Run
            </button>
          </div>
        </form>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <LineChart
          title="Price"
          ariaLabel="Price line chart"
          points={pricePoints}
          strokeFrom="rgba(249,115,22,0.88)"
          strokeTo="rgba(15,118,110,0.92)"
        />
        <LineChart title="Equity" ariaLabel="Equity line chart" points={equityPoints} />
      </section>

      <section className="overflow-hidden rounded-3xl border border-black/10 bg-white/60 shadow-[var(--shadow)]">
        <div className="flex items-center justify-between border-b border-black/10 px-6 py-4">
          <h3 className="font-display text-xl tracking-tight">Decisions</h3>
          <div className="text-xs text-black/55">{decisions.length} loaded</div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-black/50">
              <tr>
                <th className="px-6 py-3">Tick</th>
                <th className="px-6 py-3">Accepted</th>
                <th className="px-6 py-3">Target</th>
                <th className="px-6 py-3">Conf</th>
                <th className="px-6 py-3">Reason / Rationale</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-black/5">
              {decisions.map((d) => (
                <tr key={d.tick_time} className="align-top hover:bg-black/[0.02]">
                  <td className="px-6 py-3 font-mono text-xs text-black/70">
                    {fmt(d.tick_time)}
                  </td>
                  <td className="px-6 py-3">
                    <span
                      className={
                        d.accepted
                          ? "inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-900"
                          : "inline-flex rounded-full bg-rose-100 px-2.5 py-1 text-xs font-medium text-rose-900"
                      }
                    >
                      {d.accepted ? "yes" : "no"}
                    </span>
                  </td>
                  <td className="px-6 py-3 font-mono text-xs">{decisionTarget(d)}</td>
                  <td className="px-6 py-3 font-mono text-xs">{d.confidence ?? ""}</td>
                  <td className="px-6 py-3">
                    {d.reject_reason ? (
                      <div className="text-xs text-rose-800">{d.reject_reason}</div>
                    ) : null}
                    {d.rationale ? (
                      <div className="mt-1 text-sm leading-6 text-black/70">{d.rationale}</div>
                    ) : null}
                  </td>
                </tr>
              ))}
              {decisions.length === 0 ? (
                <tr>
                  <td className="px-6 py-10 text-sm text-black/55" colSpan={5}>
                    No decisions yet. Start a live run (demo mode works offline).
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
