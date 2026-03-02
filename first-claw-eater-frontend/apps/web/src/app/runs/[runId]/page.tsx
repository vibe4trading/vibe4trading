"use client";

import * as React from "react";

import { useParams } from "next/navigation";

import { LineChart } from "@/app/components/LineChart";
import { apiJson, LlmDecision, RunOut, SummaryOut, TimelinePoint } from "@/app/lib/fce";

function timeLabel(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function fmt(iso: string | null) {
  if (!iso) return "–";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function decisionTarget(dec: LlmDecision) {
  const v = dec.targets?.[dec.market_id];
  if (v !== undefined) return v;
  const firstKey = dec.targets ? Object.keys(dec.targets)[0] : undefined;
  return firstKey ? dec.targets[firstKey] : "";
}

export default function RunDetailPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;

  const [run, setRun] = React.useState<RunOut | null>(null);
  const [timeline, setTimeline] = React.useState<TimelinePoint[]>([]);
  const [decisions, setDecisions] = React.useState<LlmDecision[]>([]);
  const [summary, setSummary] = React.useState<string | null>(null);

  const PAGE_SIZE = 200;
  const [olderOffset, setOlderOffset] = React.useState(0);
  const [hasMoreDecisions, setHasMoreDecisions] = React.useState(true);
  const [loadingMore, setLoadingMore] = React.useState(false);

  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [runRes, tlRes, decRes, summaryRes] = await Promise.all([
        apiJson<RunOut>(`/runs/${runId}`),
        apiJson<TimelinePoint[]>(`/runs/${runId}/timeline`),
        apiJson<LlmDecision[]>(`/runs/${runId}/decisions?limit=${PAGE_SIZE}&offset=0`),
        apiJson<SummaryOut>(`/runs/${runId}/summary`).catch(() => ({ summary_text: null })),
      ]);
      setRun(runRes);
      setTimeline(tlRes);
      setDecisions((prev) => {
        const byTick = new Map<string, LlmDecision>();
        for (const d of prev) byTick.set(d.tick_time, d);
        for (const d of decRes) byTick.set(d.tick_time, d);
        const merged = Array.from(byTick.values());
        merged.sort((a, b) => a.tick_time.localeCompare(b.tick_time));
        return merged;
      });
      if (olderOffset === 0) {
        // Offset-based pagination can't know total count; use "page full" as a hint.
        setHasMoreDecisions(decRes.length === PAGE_SIZE);
      }
      setSummary(summaryRes.summary_text);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [runId, olderOffset]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  React.useEffect(() => {
    const status = run?.status;
    const shouldPoll =
      !status || status === "pending" || status === "running";
    if (!shouldPoll) return;

    const t = setInterval(refresh, 2500);
    return () => clearInterval(t);
  }, [refresh, run?.status]);

  async function onLoadOlder() {
    if (loadingMore || !hasMoreDecisions) return;
    setLoadingMore(true);
    setError(null);
    try {
      const nextOffset = olderOffset + PAGE_SIZE;
      const older = await apiJson<LlmDecision[]>(
        `/runs/${runId}/decisions?limit=${PAGE_SIZE}&offset=${nextOffset}`,
      );
      setOlderOffset(nextOffset);
      setHasMoreDecisions(older.length === PAGE_SIZE);
      setDecisions((prev) => {
        const byTick = new Map<string, LlmDecision>();
        for (const d of prev) byTick.set(d.tick_time, d);
        for (const d of older) byTick.set(d.tick_time, d);
        const merged = Array.from(byTick.values());
        merged.sort((a, b) => a.tick_time.localeCompare(b.tick_time));
        return merged;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingMore(false);
    }
  }

  async function onStop() {
    setError(null);
    try {
      await apiJson<{ status: string }>(`/runs/${runId}/stop`, { method: "POST" });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const equityPoints = timeline.map((p) => ({ xLabel: timeLabel(p.observed_at), y: p.equity_quote }));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-3xl tracking-tight">Run</h2>
          <div className="mt-2 grid gap-1 text-xs text-black/60 md:grid-cols-3">
            <div>
              <span className="text-black/40">run_id</span>{" "}
              <span className="font-mono">{runId}</span>
            </div>
            <div>
              <span className="text-black/40">status</span>{" "}
              <span className="font-mono">{run?.status ?? "…"}</span>
            </div>
            <div>
              <span className="text-black/40">started</span>{" "}
              <span className="font-mono">{fmt(run?.started_at ?? null)}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={refresh}
            className="rounded-full border border-black/15 bg-white/60 px-4 py-2 text-sm font-medium text-black/80 hover:bg-white"
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
          {run?.status === "running" ? (
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

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <LineChart points={equityPoints} />
        </div>
        <div className="rounded-2xl border border-black/10 bg-white/60 p-5 shadow-[var(--shadow)]">
          <div className="text-sm font-medium text-black/80">Summary</div>
          <div className="mt-3 whitespace-pre-wrap text-sm leading-6 text-black/70">
            {summary ?? (run?.status === "finished" ? "(no summary)" : "(pending)")}
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-3xl border border-black/10 bg-white/60 shadow-[var(--shadow)]">
        <div className="flex items-center justify-between border-b border-black/10 px-6 py-4">
          <h3 className="font-display text-xl tracking-tight">Decisions</h3>
          <div className="flex items-center gap-3">
            <div className="text-xs text-black/55">{decisions.length} loaded</div>
            <button
              type="button"
              onClick={onLoadOlder}
              disabled={loadingMore || !hasMoreDecisions}
              className="rounded-full border border-black/15 bg-white/60 px-3 py-1.5 text-xs font-medium text-black/75 hover:bg-white disabled:opacity-50"
            >
              {loadingMore ? "Loading…" : hasMoreDecisions ? "Load older" : "No more"}
            </button>
          </div>
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
                      <div className="mt-1 text-sm leading-6 text-black/70">
                        {d.rationale}
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
              {decisions.length === 0 ? (
                <tr>
                  <td className="px-6 py-10 text-sm text-black/55" colSpan={5}>
                    No decisions yet.
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
