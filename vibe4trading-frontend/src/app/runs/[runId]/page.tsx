import * as React from "react";
import { useTranslation } from "react-i18next";

import { useParams } from "react-router-dom";

import { CircularLoading } from "@/app/components/CircularLoading";
import { SEO } from "@/app/components/SEO";
import { LineChart } from "@/app/components/LineChart";
import { useRealtimeRefresh } from "@/app/lib/realtime";
import {
  apiJson,
  LlmDecision,
  PricePoint,
  RunConfigSnapshot,
  RunOut,
  SummaryOut,
  TimelinePoint,
} from "@/app/lib/v4t";

function fmt(iso: string | null) {
  if (!iso) return "–";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function timeLabel(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function pairName(marketId: string | null | undefined) {
  if (!marketId) return "–";
  const parts = marketId.split(":");
  return parts[parts.length - 1] ?? marketId;
}

function pct(value: number | null | undefined, digits = 2) {
  if (value == null || Number.isNaN(value)) return "–";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

function fixed(value: number | null | undefined, digits = 2) {
  if (value == null || Number.isNaN(value)) return "–";
  return value.toFixed(digits);
}

function toneClass(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return "neutral";
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}

function decisionTarget(decision: LlmDecision) {
  const current = decision.targets?.[decision.market_id];
  if (current !== undefined) return current;
  const firstKey = decision.targets ? Object.keys(decision.targets)[0] : undefined;
  return firstKey ? decision.targets[firstKey] : "";
}

function computeMaxDrawdownPct(series: number[]) {
  if (series.length < 2) return null;
  let peak = series[0];
  let maxDrawdown = 0;
  for (const value of series.slice(1)) {
    peak = Math.max(peak, value);
    if (peak > 0) {
      maxDrawdown = Math.max(maxDrawdown, ((peak - value) / peak) * 100);
    }
  }
  return maxDrawdown;
}

function computeScore(
  totalReturnPct: number | null,
  maxDrawdownPct: number | null,
  acceptanceRatePct: number | null,
) {
  const score =
    50 +
    (totalReturnPct ?? 0) * 1.4 -
    (maxDrawdownPct ?? 0) * 0.8 +
    ((acceptanceRatePct ?? 50) - 50) * 0.18;
  return Math.max(0, Math.min(99, Math.round(score)));
}

function verdictLabel(totalReturnPct: number | null, maxDrawdownPct: number | null) {
  if (totalReturnPct == null) return "Awaiting run summary";
  if (totalReturnPct >= 12 && (maxDrawdownPct ?? 99) <= 8) return "Trend capture with disciplined risk";
  if (totalReturnPct >= 0) return "Constructive run with manageable variance";
  if ((maxDrawdownPct ?? 0) >= 15) return "High-variance run with weak downside control";
  return "Run finished below water";
}

function buildFallbackSummary(
  run: RunOut | null,
  totalReturnPct: number | null,
  maxDrawdownPct: number | null,
  latestTarget: string,
  decisionCount: number,
) {
  if (!run) return "Loading run report.";
  return `Run ${run.run_id.slice(0, 8)} on ${pairName(run.market_id)} finished ${run.status}. Total return ${pct(totalReturnPct)}, max drawdown ${pct(maxDrawdownPct)}, ${decisionCount} decisions recorded, latest target ${latestTarget}.`;
}

export default function RunDetailPage() {
  const { t } = useTranslation("runs");
  const runId = useParams<{ runId: string }>().runId ?? "";

  const [run, setRun] = React.useState<RunOut | null>(null);
  const [config, setConfig] = React.useState<RunConfigSnapshot | null>(null);
  const [timeline, setTimeline] = React.useState<TimelinePoint[]>([]);
  const [prices, setPrices] = React.useState<PricePoint[]>([]);
  const [decisions, setDecisions] = React.useState<LlmDecision[]>([]);
  const [summary, setSummary] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    try {
      const [runRes, configRes, timelineRes, priceRes, decisionRes, summaryRes] = await Promise.all([
        apiJson<RunOut>(`/runs/${runId}`),
        apiJson<RunConfigSnapshot>(`/runs/${runId}/config`),
        apiJson<TimelinePoint[]>(`/runs/${runId}/timeline`),
        apiJson<PricePoint[]>(`/runs/${runId}/prices?limit=600`),
        apiJson<LlmDecision[]>(`/runs/${runId}/decisions?limit=200&offset=0`),
        apiJson<SummaryOut>(`/runs/${runId}/summary`).catch(() => ({ summary_text: null })),
      ]);
      setRun(runRes);
      setConfig(configRes);
      setTimeline(timelineRes);
      setPrices(priceRes);
      setDecisions(decisionRes);
      setSummary(summaryRes.summary_text);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load run.");
    } finally {
      setLoading(false);
    }
  }, [runId]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const status = run?.status;
  const shouldRefresh = !status || status === "pending" || status === "running" || status === "submitted";
  useRealtimeRefresh({
    wsPath: shouldRefresh ? `/runs/${runId}/ws` : null,
    enabled: shouldRefresh,
    pollIntervalMs: 2500,
    refresh,
  });

  const initialEquity =
    config?.execution?.initial_equity_quote ??
    (timeline.length > 0 ? timeline[0].equity_quote : null);
  const latestSnapshot = timeline.length > 0 ? timeline[timeline.length - 1] : null;
  const latestPrice = prices.length > 0 ? prices[prices.length - 1] : null;
  const latestDecision = decisions.length > 0 ? decisions[decisions.length - 1] : null;

  const totalReturnPct =
    initialEquity != null && initialEquity !== 0 && latestSnapshot
      ? ((latestSnapshot.equity_quote - initialEquity) / initialEquity) * 100
      : null;
  const priceChangePct =
    prices.length > 1 && prices[0].price !== 0
      ? ((prices[prices.length - 1].price - prices[0].price) / prices[0].price) * 100
      : null;
  const maxDrawdownPct = computeMaxDrawdownPct(timeline.map((point) => point.equity_quote));

  const acceptedCount = decisions.filter((decision) => decision.accepted).length;
  const acceptanceRatePct =
    decisions.length > 0 ? (acceptedCount / decisions.length) * 100 : null;

  const numericTargets = decisions
    .map((decision) => Number.parseFloat(decisionTarget(decision)))
    .filter((value) => Number.isFinite(value));
  const avgTarget =
    numericTargets.length > 0
      ? numericTargets.reduce((sum, value) => sum + value, 0) / numericTargets.length
      : null;

  const cashRatioPct =
    latestSnapshot && latestSnapshot.equity_quote !== 0
      ? (latestSnapshot.cash_quote / latestSnapshot.equity_quote) * 100
      : null;

  const score = computeScore(totalReturnPct, maxDrawdownPct, acceptanceRatePct);
  const latestTarget = latestDecision ? decisionTarget(latestDecision) || "hold" : "hold";
  const heroSummary =
    summary ??
    buildFallbackSummary(run, totalReturnPct, maxDrawdownPct, latestTarget, decisions.length);

  const equityPoints = React.useMemo(
    () =>
      timeline.map((point) => ({
        xLabel: timeLabel(point.observed_at),
        y: point.equity_quote,
      })),
    [timeline],
  );

  const pricePoints = React.useMemo(
    () =>
      prices.map((point) => ({
        xLabel: timeLabel(point.observed_at),
        y: point.price,
      })),
    [prices],
  );

  const recentDecisions = React.useMemo(() => [...decisions].slice(-10).reverse(), [decisions]);

  if (error && !run) {
    return (
      <main className="mx-auto flex min-h-[60vh] max-w-3xl flex-col items-start justify-center px-6 py-16">
        <div className="w-full border-2 border-[#c0392b] bg-[#f9e5e5] p-6 text-[#8f2d24]">
          <h1 className="text-2xl font-bold text-[#5c201a]">{t("detail.error.title")}</h1>
          <p className="mt-3 text-sm">{error}</p>
          <button
            type="button"
            onClick={() => {
              void refresh();
            }}
            className="mt-5 border-2 border-[#5c201a] bg-white px-5 py-2 text-sm font-semibold text-[#5c201a] transition-colors hover:bg-[#f4d6d1]"
          >
            {t("detail.error.retry")}
          </button>
        </div>
      </main>
    );
  }

  if (loading && !run) {
    return <CircularLoading status="pending" />;
  }

  if (shouldRefresh && timeline.length === 0 && prices.length === 0 && decisions.length === 0) {
    return <CircularLoading status={run?.status || "pending"} />;
  }

  return (
    <main className="layout animate-rise">
      <SEO title={t("detail.title")} description={t("detail.description")} noindex />
      <section className="left-column">
        <article className="hero-card block">
          <div className="hero-meta">
            {t("detail.hero.meta", { model: run?.model_key ?? "UNKNOWN", time: fmt(run?.started_at ?? run?.created_at ?? null) })}
          </div>
          <div className="hero-title-row">
            <div className="score">
              <div className="score-label">{t("detail.hero.scoreLabel")}</div>
              <div className="score-value">{String(score).padStart(2, "0")}</div>
            </div>
            <div className="persona">
              <h1>{verdictLabel(totalReturnPct, maxDrawdownPct)}</h1>
              <p>
                {pairName(run?.market_id)} / {run?.model_key ?? "model"} / {t("detail.hero.latestTarget")} {latestTarget}
              </p>
              <div className="tags">
                <span>{run?.status ?? "unknown"}</span>
                <span>{config?.prompt?.timeframe ?? "1h"}</span>
                <span>{t("detail.hero.decisionsCount", { count: decisions.length })}</span>
                <span>{initialEquity != null ? t("detail.hero.startBalance", { amount: fixed(initialEquity, 0) }) : t("detail.hero.startNA")}</span>
                {shouldRefresh ? <span>{t("detail.hero.autoRefresh")}</span> : null}
              </div>
            </div>
          </div>
          <p className="hero-summary">{heroSummary}</p>
          {error ? (
            <p className="hero-meta" style={{ color: "var(--red)" }}>
              {error}
            </p>
          ) : null}
        </article>

        <section className="metric-grid">
          <article className="metric block">
            <h3>{t("detail.metrics.totalReturn")}</h3>
            <p className={`value ${toneClass(totalReturnPct)}`}>{pct(totalReturnPct)}</p>
            <p className="rank good">{t("detail.metrics.totalReturnDesc")}</p>
          </article>
          <article className="metric block">
            <h3>{t("detail.metrics.maxDrawdown")}</h3>
            <p className={`value ${toneClass(maxDrawdownPct == null ? null : -maxDrawdownPct)}`}>
              {pct(maxDrawdownPct == null ? null : -maxDrawdownPct)}
            </p>
            <p className="rank mid">{t("detail.metrics.maxDrawdownDesc")}</p>
          </article>
          <article className="metric block">
            <h3>{t("detail.metrics.acceptance")}</h3>
            <p className="value neutral">{pct(acceptanceRatePct, 1)}</p>
            <p className="rank elite">{t("detail.metrics.acceptanceDesc", { count: acceptedCount })}</p>
          </article>
          <article className="metric block">
            <h3>{t("detail.metrics.avgTarget")}</h3>
            <p className={`value ${toneClass(avgTarget == null ? null : avgTarget - 0.5)}`}>
              {avgTarget == null ? "–" : fixed(avgTarget, 2)}
            </p>
            <p className="rank good">{t("detail.metrics.avgTargetDesc")}</p>
          </article>
          <article className="metric block">
            <h3>{t("detail.metrics.cashRatio")}</h3>
            <p className="value neutral">{pct(cashRatioPct, 1)}</p>
            <p className="rank mid">
              {latestSnapshot ? t("detail.metrics.cashRatioValue", { amount: fixed(latestSnapshot.cash_quote, 2) }) : t("detail.metrics.cashRatioNA")}
            </p>
          </article>
        </section>

        <div className="grid gap-4 xl:grid-cols-2">
          <LineChart
            title={t("detail.charts.equity")}
            ariaLabel={t("detail.charts.equityAria")}
            points={equityPoints}
            variant="light"
            strokeFrom="rgba(59,102,217,0.9)"
            strokeTo="rgba(10,141,73,0.82)"
          />
          <LineChart
            title={t("detail.charts.price")}
            ariaLabel={t("detail.charts.priceAria")}
            points={pricePoints}
            variant="light"
            strokeFrom="rgba(206,93,18,0.92)"
            strokeTo="rgba(59,102,217,0.8)"
          />
        </div>

        <article className="block">
          <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="m-0 text-[28px]">{t("detail.decisions.heading")}</h2>
              <p className="mt-2 mb-0 text-[16px] text-[var(--muted)]">
                {t("detail.decisions.description")}
              </p>
            </div>
            <div className="text-[16px] text-[var(--muted)]">
              {t("detail.decisions.priceMove", { change: pct(priceChangePct), price: latestPrice ? fixed(latestPrice.price, 4) : "–" })}
            </div>
          </div>

          <div className="mt-4 overflow-x-auto border-2 border-[var(--line)] bg-[#fbfbf8]">
            <table className="w-full min-w-[760px] border-collapse text-left text-[14px]">
              <thead className="border-b-2 border-[var(--line)] bg-[#eceae3]">
                <tr>
                  <th className="px-3 py-2">{t("detail.decisions.table.tick")}</th>
                  <th className="px-3 py-2">{t("detail.decisions.table.accepted")}</th>
                  <th className="px-3 py-2">{t("detail.decisions.table.target")}</th>
                  <th className="px-3 py-2">{t("detail.decisions.table.signals")}</th>
                  <th className="px-3 py-2">{t("detail.decisions.table.rationale")}</th>
                </tr>
              </thead>
              <tbody>
                {recentDecisions.map((decision) => (
                  <tr key={`${decision.tick_time}-${decision.llm_call_id ?? "decision"}`} className="border-b border-[#d2d0c9] align-top">
                    <td className="px-3 py-2">{fmt(decision.tick_time)}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-flex border px-2 py-1 text-[11px] uppercase tracking-[0.12em] ${
                          decision.accepted
                            ? "border-[#2d7f4c] bg-[#d6f0dc] text-[#1d7e4b]"
                            : "border-[#c0392b] bg-[#f9e5e5] text-[#c0392b]"
                        }`}
                      >
                        {decision.accepted ? t("detail.decisions.table.acceptedLabel") : t("detail.decisions.table.rejectedLabel")}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono">{decisionTarget(decision) || "hold"}</td>
                    <td className="px-3 py-2">{decision.key_signals?.join(", ") || "–"}</td>
                    <td className="px-3 py-2 text-[13px] leading-6 text-[#444]">
                      {decision.reject_reason ? `[${decision.reject_reason}] ` : ""}
                      {decision.rationale || "–"}
                    </td>
                  </tr>
                ))}
                {recentDecisions.length === 0 ? (
                  <tr>
                    <td className="px-3 py-8 text-center text-[var(--muted)]" colSpan={5}>
                      {t("detail.decisions.table.empty")}
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <aside className="right-column">
        <div className="grid gap-3">
          <section className="block">
            <h2 className="m-0 text-[24px]">{t("detail.sidebar.snapshot.heading")}</h2>
            <div className="mt-4 grid gap-2 text-[15px]">
              <div className="flex items-center justify-between gap-3 border-b border-[#d2d0c9] pb-2">
                <span>{t("detail.sidebar.snapshot.status")}</span>
                <strong>{(run?.status ?? "unknown").toUpperCase()}</strong>
              </div>
              <div className="flex items-center justify-between gap-3 border-b border-[#d2d0c9] pb-2">
                <span>{t("detail.sidebar.snapshot.runId")}</span>
                <strong>{run ? `${run.run_id.slice(0, 8)}…` : "–"}</strong>
              </div>
              <div className="flex items-center justify-between gap-3 border-b border-[#d2d0c9] pb-2">
                <span>{t("detail.sidebar.snapshot.pair")}</span>
                <strong>{pairName(run?.market_id)}</strong>
              </div>
              <div className="flex items-center justify-between gap-3 border-b border-[#d2d0c9] pb-2">
                <span>{t("detail.sidebar.snapshot.model")}</span>
                <strong>{run?.model_key ?? "–"}</strong>
              </div>
              <div className="flex items-center justify-between gap-3 border-b border-[#d2d0c9] pb-2">
                <span>{t("detail.sidebar.snapshot.started")}</span>
                <strong>{fmt(run?.started_at ?? run?.created_at ?? null)}</strong>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>{t("detail.sidebar.snapshot.ended")}</span>
                <strong>{fmt(run?.ended_at ?? null)}</strong>
              </div>
            </div>
          </section>

          <section className="block">
            <h2 className="m-0 text-[24px]">{t("detail.sidebar.config.heading")}</h2>
            <div className="mt-4 grid gap-2 text-[15px]">
              <div className="flex items-center justify-between gap-3 border-b border-[#d2d0c9] pb-2">
                <span>{t("detail.sidebar.config.startBalance")}</span>
                <strong>
                  {config?.execution?.initial_equity_quote != null
                    ? fixed(config.execution.initial_equity_quote, 0)
                    : "–"}
                </strong>
              </div>
              <div className="flex items-center justify-between gap-3 border-b border-[#d2d0c9] pb-2">
                <span>{t("detail.sidebar.config.fee")}</span>
                <strong>{config?.execution?.fee_bps != null ? fixed(config.execution.fee_bps, 1) : "–"}</strong>
              </div>
              <div className="flex items-center justify-between gap-3 border-b border-[#d2d0c9] pb-2">
                <span>{t("detail.sidebar.config.lookbackBars")}</span>
                <strong>{config?.prompt?.lookback_bars ?? "–"}</strong>
              </div>
              <div className="flex items-center justify-between gap-3 border-b border-[#d2d0c9] pb-2">
                <span>{t("detail.sidebar.config.timeframe")}</span>
                <strong>{config?.prompt?.timeframe ?? "–"}</strong>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>{t("detail.sidebar.config.include")}</span>
                <strong>{config?.prompt?.include?.join(", ") ?? "default"}</strong>
              </div>
            </div>
          </section>

          <section className="block">
            <h2 className="m-0 text-[24px]">{t("detail.sidebar.prompt.heading")}</h2>
            <pre className="mt-4 overflow-x-auto whitespace-pre-wrap border-2 border-[var(--line)] bg-[#fbfbf8] p-3 text-[13px] leading-6 text-[#2d2d2d]">
              {config?.prompt?.prompt_text?.trim() || t("detail.sidebar.prompt.empty")}
            </pre>
          </section>

          <section className="block">
            <h2 className="m-0 text-[24px]">{t("detail.sidebar.latestDecision.heading")}</h2>
            {latestDecision ? (
              <div className="mt-4 grid gap-3 text-[14px]">
                <div className="border-2 border-[var(--line)] bg-[#fbfbf8] p-3">
                  <div className="text-[12px] uppercase tracking-[0.12em] text-[var(--muted)]">{t("detail.sidebar.latestDecision.tick")}</div>
                  <div className="mt-1 text-[16px]">{fmt(latestDecision.tick_time)}</div>
                </div>
                <div className="border-2 border-[var(--line)] bg-[#fbfbf8] p-3">
                  <div className="text-[12px] uppercase tracking-[0.12em] text-[var(--muted)]">{t("detail.sidebar.latestDecision.target")}</div>
                  <div className="mt-1 font-mono text-[18px]">{latestTarget}</div>
                </div>
                <div className="border-2 border-[var(--line)] bg-[#fbfbf8] p-3">
                  <div className="text-[12px] uppercase tracking-[0.12em] text-[var(--muted)]">{t("detail.sidebar.latestDecision.confidence")}</div>
                  <div className="mt-1 text-[16px]">
                    {latestDecision.confidence != null ? fixed(Number(latestDecision.confidence), 2) : "–"}
                  </div>
                </div>
                <div className="border-2 border-[var(--line)] bg-[#fbfbf8] p-3 text-[13px] leading-6 text-[#444]">
                  {latestDecision.rationale || t("detail.sidebar.latestDecision.noRationale")}
                </div>
              </div>
            ) : (
              <p className="mt-4 mb-0 text-[15px] text-[var(--muted)]">{t("detail.sidebar.latestDecision.empty")}</p>
            )}
          </section>
        </div>
      </aside>
    </main>
  );
}
