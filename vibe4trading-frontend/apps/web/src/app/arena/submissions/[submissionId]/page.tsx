"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import {
  apiJson,
  ArenaSubmissionDetailOut,
  ArenaScenarioRunOut,
} from "@/app/lib/v4t";
import { useRealtimeRefresh } from "@/app/lib/realtime";

function fmt(dt: string | null) {
  if (!dt) return "–";
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return dt;
  }
}

function pct(v: number | null) {
  if (v === null || Number.isNaN(v)) return "–";
  const s = v >= 0 ? `+${v.toFixed(2)}` : v.toFixed(2);
  return `${s}%`;
}

function pctColor(v: number | null) {
  if (v === null || Number.isNaN(v)) return "text-zinc-400";
  return v >= 0
    ? "text-[color:var(--accent)] drop-shadow-[0_0_6px_var(--accent-glow)] font-bold"
    : "text-rose-400 drop-shadow-[0_0_6px_rgba(244,63,94,0.15)] font-bold";
}

function badge(status: string) {
  if (status === "finished") return "bg-[color:var(--accent)]/10 text-[color:var(--accent)] border border-[color:var(--accent)]/30 drop-shadow-[0_0_8px_var(--accent-glow)]";
  if (status === "running") return "bg-[color:var(--accent-2)]/10 text-[color:var(--accent-2)] border border-[color:var(--accent-2)]/30 drop-shadow-[0_0_8px_var(--accent-2-glow)]";
  if (status === "failed") return "bg-rose-500/10 text-rose-400 border border-rose-500/30 drop-shadow-[0_0_8px_rgba(244,63,94,0.15)]";
  if (status === "cancelled") return "bg-zinc-500/10 text-zinc-400 border border-zinc-500/30";
  return "bg-zinc-500/10 text-zinc-400 border border-zinc-500/30";
}

function windowLabel(scenarioSetKey: string | null | undefined, idx: number) {
  if (scenarioSetKey === "env-regimes-v1") {
    const labels = ["Black Swan", "Bull Run", "Vol Spike", "Low Vol", "Sideways"];
    return labels[idx] ?? `Regime ${idx + 1}`;
  }
  if (scenarioSetKey === "env-fullrange-v1") {
    if (idx === 0) return "Full Range";
    return `Window ${idx + 1}`;
  }
  return `Window ${idx + 1}`;
}

function runStatus(r: ArenaScenarioRunOut) {
  return r.status;
}

export default function SubmissionDetailPage() {
  const params = useParams<{ submissionId: string }>();
  const submissionId = params.submissionId;

  const [data, setData] = React.useState<ArenaSubmissionDetailOut | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiJson<ArenaSubmissionDetailOut>(
        `/arena/submissions/${submissionId}`,
      );
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [submissionId]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const shouldRefresh = !data?.status || data.status === "pending" || data.status === "running";
  useRealtimeRefresh({
    wsPath: "/runs/ws",
    enabled: shouldRefresh,
    pollIntervalMs: 2500,
    refresh,
  });

  return (
    <div className="flex flex-col gap-8 animate-rise">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold tracking-widest text-[color:var(--accent-2)]">
            TOURNAMENT RUN
          </p>
          <h2 className="mt-2 font-display text-4xl tracking-tight text-white drop-shadow-sm">Run</h2>
          <div className="mt-3 grid gap-4 text-sm text-zinc-400 md:grid-cols-3">
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">submission_id</span>
              <span className="font-mono text-white/90">{submissionId}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">status</span>
              <span data-testid="tournament-run-status" className="font-mono text-white/90">
                {data?.status ?? "…"}
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">progress</span>
              <span data-testid="tournament-run-progress" className="font-mono text-white/90">
                {data ? `${data.windows_completed}/${data.windows_total}` : "…"}
              </span>
            </div>
          </div>
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

      {(() => {
        const status = (data?.status ?? "pending").toLowerCase();
        const isWorking = !data || status === "pending" || status === "running";
        if (!isWorking) return null;

        const done = data?.windows_completed ?? 0;
        const total = data?.windows_total ?? 0;
        const pct = total > 0 ? Math.min(100, Math.max(0, (done / total) * 100)) : 0;

        return (
          <section className="animate-rise-1 rounded-3xl border border-[color:var(--border)] bg-white/5 p-8 shadow-lg backdrop-blur-md">
            <div className="flex flex-col items-center gap-5 text-center">
              <div className="relative h-16 w-16">
                <div className="absolute inset-0 rounded-full border border-white/10 bg-black/20" />
                <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-[color:var(--accent-2)]/90 animate-spin" />
                <div className="absolute inset-2 rounded-full bg-[color:var(--accent)]/10 blur-sm" />
              </div>

              <div>
                <div className="font-display text-2xl tracking-tight text-white">
                  Starting your run
                </div>
                <div className="mt-2 text-sm text-zinc-400">
                  {total > 0 ? `Scenarios completed: ${done}/${total}` : "Queueing scenario windows..."}
                </div>
              </div>

              <div className="w-full max-w-md">
                <div className="h-2 w-full overflow-hidden rounded-full bg-black/30">
                  <div
                    className="h-full rounded-full bg-[linear-gradient(90deg,var(--accent-2),var(--accent))] transition-[width] duration-300"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className="mt-2 text-xs font-medium tracking-wider text-zinc-500">
                  This page auto-refreshes while the run is pending/running.
                </div>
              </div>
            </div>
          </section>
        );
      })()}

      <section className="animate-rise-1 grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-[color:var(--border)] bg-white/5 p-6 shadow-lg backdrop-blur-md">
          <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Result</div>
          <div className={`mt-2 font-display text-2xl tracking-tight ${data?.status === "finished" ? pctColor(data.total_return_pct) : "text-white"}`}>
            {data?.status === "finished" ? pct(data.total_return_pct) : "(pending)"}
          </div>
          <div className="mt-2 text-sm text-zinc-400">
            Avg window: <span className={data?.avg_return_pct != null ? pctColor(data.avg_return_pct) : "text-zinc-400"}>{data?.avg_return_pct == null ? "–" : pct(data.avg_return_pct)}</span>
          </div>
          {data?.error ? (
            <div className="mt-3 text-sm text-rose-400">{data.error}</div>
          ) : null}
        </div>

        <div className="rounded-2xl border border-[color:var(--border)] bg-white/5 p-6 shadow-lg backdrop-blur-md">
          <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Config</div>
          <div className="mt-3 grid gap-2 text-xs text-zinc-400">
            <div className="flex flex-col gap-1">
              <span className="text-zinc-500">scenario_set</span>
              <span className="font-mono text-white/90">{data?.scenario_set_key ?? "…"}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-zinc-500">market_id</span>
              <span className="font-mono text-[color:var(--accent)]">{data?.market_id ?? "…"}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-zinc-500">model_key</span>
              <span className="font-mono text-[color:var(--accent-2)]">{data?.model_key ?? "…"}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-zinc-500">visibility</span>
              <span className="font-mono text-white/90">{data?.visibility ?? "…"}</span>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-[color:var(--border)] bg-white/5 p-6 shadow-lg backdrop-blur-md">
          <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Timing</div>
          <div className="mt-3 grid gap-2 text-xs text-zinc-400">
            <div className="flex flex-col gap-1">
              <span className="text-zinc-500">created</span>
              <span className="font-mono text-white/90">{fmt(data?.created_at ?? null)}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-zinc-500">started</span>
              <span className="font-mono text-white/90">{fmt(data?.started_at ?? null)}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-zinc-500">ended</span>
              <span className="font-mono text-white/90">{fmt(data?.ended_at ?? null)}</span>
            </div>
          </div>
        </div>
      </section>

      <section className="animate-rise-2 overflow-hidden rounded-3xl border border-[color:var(--border)] bg-white/5 shadow-lg backdrop-blur-md">
        <div className="flex items-center justify-between border-b border-white/10 bg-white/5 px-6 py-5">
          <h3 className="font-display text-xl tracking-tight text-white flex items-center gap-2">
            <svg className="w-5 h-5 text-[color:var(--accent-2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Scenario Runs
          </h3>
          <div className="rounded-full bg-white/10 px-3 py-1.5 text-xs font-medium text-white shadow-inner">
            {data?.runs.length ?? 0} windows
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-black/20 text-xs uppercase tracking-wider text-zinc-400">
              <tr>
                <th className="px-6 py-4 font-semibold">#</th>
                <th className="px-6 py-4 font-semibold">Window</th>
                <th className="px-6 py-4 font-semibold">Run</th>
                <th className="px-6 py-4 font-semibold">Status</th>
                <th className="px-6 py-4 font-semibold">Return</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {(data?.runs ?? []).map((r) => (
                <tr key={`${r.submission_id}:${r.scenario_index}`} className="transition-colors hover:bg-white/5">
                  <td className="px-6 py-4 font-mono text-xs text-white font-bold">
                    {r.scenario_index}
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-xs font-semibold tracking-wide text-white/90">
                      {windowLabel(data?.scenario_set_key, r.scenario_index)}
                    </div>
                    <div className="font-mono text-xs text-zinc-300">
                      {fmt(r.window_start)}
                    </div>
                    <div className="mt-1 font-mono text-xs text-zinc-500">
                      to {fmt(r.window_end)}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {data?.visibility === "private" ? (
                      <span className="font-mono text-xs text-zinc-500">(hidden)</span>
                    ) : (
                      <Link
                        href={`/runs/${r.run_id}`}
                        className="font-mono text-xs text-[color:var(--accent)] hover:text-white transition-colors"
                      >
                        {r.run_id.slice(0, 8)}…
                      </Link>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wider ${badge(
                        runStatus(r),
                      )}`}
                    >
                      {runStatus(r) === "running" && (
                        <span className="relative flex h-1.5 w-1.5">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-current"></span>
                        </span>
                      )}
                      {runStatus(r)}
                    </span>
                    {r.error ? (
                      <div className="mt-2 text-xs text-rose-400">{r.error}</div>
                    ) : null}
                  </td>
                  <td className={`px-6 py-4 font-mono text-xs ${r.status === "finished" ? pctColor(r.return_pct) : "text-zinc-600"}`}>
                    {r.status === "finished" ? pct(r.return_pct) : "–"}
                  </td>
                </tr>
              ))}
              {(data?.runs?.length ?? 0) === 0 ? (
                <tr>
                  <td className="px-6 py-12 text-center text-sm text-zinc-500" colSpan={5}>
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <svg className="h-10 w-10 text-zinc-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                      <p>No scenario runs yet.</p>
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
