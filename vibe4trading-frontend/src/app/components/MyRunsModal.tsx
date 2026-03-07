import { Link } from "react-router-dom";
import * as React from "react";

import { useModalA11y } from "@/app/hooks/useModalA11y";
import { getSubmissionStatusDisplay } from "@/app/lib/submissionStatus";
import { ArenaSubmissionOut } from "@/app/lib/v4t";

function fmt(dt: string | null) {
  if (!dt) return "\u2013";
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return dt;
  }
}

function pct(v: number | null) {
  if (v == null || Number.isNaN(v)) return "\u2013";
  const s = v >= 0 ? `+${v.toFixed(2)}` : v.toFixed(2);
  return `${s}%`;
}

function submissionBadge(status: string) {
  if (status === "Finished")
    return "bg-[color:var(--accent)]/10 text-[color:var(--accent)] border border-[color:var(--accent)]/30 drop-shadow-[0_0_8px_var(--accent-glow)]";
  if (status === "Running")
    return "bg-[color:var(--accent-2)]/10 text-[color:var(--accent-2)] border border-[color:var(--accent-2)]/30 drop-shadow-[0_0_8px_var(--accent-2-glow)]";
  if (status === "Queued")
    return "bg-amber-500/10 text-amber-300 border border-amber-500/30 drop-shadow-[0_0_8px_rgba(245,158,11,0.18)]";
  if (status === "Failed")
    return "bg-rose-500/10 text-rose-400 border border-rose-500/30 drop-shadow-[0_0_8px_rgba(244,63,94,0.15)]";
  return "bg-zinc-500/10 text-zinc-400 border border-zinc-500/30";
}

type MyRunsModalProps = {
  open: boolean;
  submissions: ArenaSubmissionOut[];
  onClose: () => void;
};

export function MyRunsModal({ open, submissions, onClose }: MyRunsModalProps) {
  const { panelRef } = useModalA11y(open, onClose);
  const titleId = React.useId();

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-40 flex items-end justify-center px-5 py-6 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onMouseDown={onClose}
        aria-hidden="true"
      />

      <div
        ref={panelRef as React.RefObject<HTMLDivElement>}
        className="relative w-full max-w-3xl max-h-[calc(100vh-3rem)] overflow-hidden rounded-3xl border border-white/10 bg-[color:var(--surface)] shadow-[0_20px_80px_rgba(0,0,0,0.6)] flex flex-col"
      >
        <div className="flex items-start justify-between gap-4 border-b border-white/10 bg-white/5 px-6 py-5">
          <div>
            <div className="text-xs font-bold tracking-widest text-[color:var(--accent-2)]">
              TOURNAMENT
            </div>
            <h3 id={titleId} className="mt-1 font-display text-2xl tracking-tight text-white">
              My Runs
            </h3>
            <p className="mt-2 text-sm text-zinc-400">
              Your tournament submissions and their results.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-zinc-200 transition-all hover:bg-white/10 hover:text-white"
          >
            Close
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {submissions.length === 0 ? (
            <div className="flex flex-col items-center justify-center space-y-3 py-16">
              <svg
                className="h-10 w-10 text-zinc-700"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1}
                  d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                />
              </svg>
              <p className="text-sm text-zinc-500">No submissions yet. Start a new run!</p>
            </div>
          ) : (
            <table className="min-w-full text-left text-sm">
              <thead className="bg-black/20 text-xs uppercase tracking-wider text-zinc-400 sticky top-0">
                <tr>
                  <th className="px-6 py-4 font-semibold">Submission</th>
                  <th className="px-6 py-4 font-semibold">Status</th>
                  <th className="px-6 py-4 font-semibold">Progress</th>
                  <th className="px-6 py-4 font-semibold">Total</th>
                  <th className="px-6 py-4 font-semibold">Market</th>
                  <th className="px-6 py-4 font-semibold">Model</th>
                  <th className="px-6 py-4 font-semibold">Created</th>
                </tr>
              </thead>
                <tbody className="divide-y divide-white/10">
                {submissions.map((s) => {
                  const statusDisplay = getSubmissionStatusDisplay({
                    status: s.status,
                    startedAt: s.started_at,
                  });

                  return (
                    <tr key={s.submission_id} className="transition-colors hover:bg-white/5">
                      <td className="px-6 py-4">
                        <Link
                          className="font-mono text-xs text-[color:var(--accent)] hover:text-white transition-colors"
                          to={`/arena/submissions/${s.submission_id}`}
                          onClick={onClose}
                        >
                          {s.submission_id.slice(0, 8)}&hellip;
                        </Link>
                        <div className="mt-1.5 text-xs font-medium text-zinc-500">
                          {s.scenario_set_key}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wider shadow-[0_0_10px_rgba(0,0,0,0.2)] ${submissionBadge(statusDisplay.label)}`}
                        >
                          {statusDisplay.label === "Running" && (
                            <span className="relative flex h-1.5 w-1.5">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75" />
                              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-current" />
                            </span>
                          )}
                          {statusDisplay.label}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-white">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{s.windows_completed}</span>
                          <span className="text-zinc-500">/</span>
                          <span className="text-zinc-400">{s.windows_total}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs">
                        {s.status === "finished" ? (
                          <span
                            className={
                              s.total_return_pct && s.total_return_pct >= 0
                                ? "text-[color:var(--accent)] drop-shadow-[0_0_8px_var(--accent-glow)] font-bold"
                                : "text-rose-400 drop-shadow-[0_0_8px_rgba(244,63,94,0.15)] font-bold"
                            }
                          >
                            {pct(s.total_return_pct)}
                          </span>
                        ) : (
                          <span className="text-zinc-600">&ndash;</span>
                        )}
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-zinc-300">{s.market_id}</td>
                      <td className="px-6 py-4">
                        <span className="font-mono text-xs text-[color:var(--accent-2)]">
                          {s.model_key}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-zinc-400">{fmt(s.created_at)}</td>
                    </tr>
                  );
                })}
                </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
