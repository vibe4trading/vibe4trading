import { Link } from "react-router-dom";
import { useParams } from "react-router-dom";
import * as React from "react";

import { SEO } from "@/app/components/SEO";
import { useRealtimeRefresh } from "@/app/lib/realtime";
import { storyCards } from "@/app/lib/report-data";
import { getSubmissionStatusDisplay } from "@/app/lib/submissionStatus";
import { useModalA11y } from "@/app/hooks/useModalA11y";
import {
  apiJson,
  ArenaScenarioRunOut,
  ArenaSubmissionDetailOut,
  ArenaSubmissionReportWindow,
} from "@/app/lib/v4t";
import { useProductTour } from "@/app/hooks/useProductTour";
import { useTourPersistence } from "@/app/hooks/useTourPersistence";
import { useTourContext } from "@/app/components/TourProvider";
import { submissionDetailSteps } from "@/app/tours/submission-detail-tour";
import { useTranslation } from "react-i18next";

function pairName(marketId: string | null | undefined) {
  if (!marketId) return "–";
  const parts = marketId.split(":");
  return parts[parts.length - 1] ?? marketId;
}

function fmt(dt: string | null | undefined) {
  if (!dt) return "–";
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return dt;
  }
}

function fmtShort(dt: string | null | undefined) {
  if (!dt) return "–";
  try {
    return new Date(dt).toLocaleString([], {
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dt;
  }
}

function pct(v: number | null | undefined) {
  if (v == null || Number.isNaN(v)) return "–";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

function pctTone(v: number | null | undefined) {
  if (v == null || Number.isNaN(v)) return "neutral";
  return v >= 0 ? "positive" : "negative";
}

function fallbackScoreValue(totalReturnPct: number | null, winRatePct: number | null, progressPct: number) {
  const score = 50 + (totalReturnPct ?? 0) * 1.4 + ((winRatePct ?? 50) - 50) * 0.45 + progressPct * 0.12;
  return Math.max(0, Math.min(99, Math.round(score)));
}

function statusMark(status: string, ret: number | null | undefined) {
  const normalized = status.toLowerCase();
  if (normalized === "running" || normalized === "pending" || normalized === "submitted") return "warn";
  if (normalized === "failed" || normalized === "cancelled") return "crash";
  if (ret == null || Number.isNaN(ret)) return "neutral";
  if (ret >= 2) return "strong";
  if (ret >= 0) return "avg";
  return "weak";
}

function statusCellClass(status: string) {
  const normalized = status.toLowerCase();
  if (normalized === "finished") return "strong";
  if (normalized === "running" || normalized === "pending" || normalized === "submitted") return "avg";
  if (normalized === "failed" || normalized === "cancelled") return "weak";
  return "";
}

function windowCode(index: number) {
  return `W${String(index + 1).padStart(2, "0")}`;
}

function windowLabel(scenarioSetKey: string | null | undefined, idx: number, t?: (key: string) => string) {
  if (scenarioSetKey === "env-regimes-v1") {
    const labels = ["Black Swan", "Bull Run", "Vol Spike", "Low Vol", "Sideways"];
    return labels[idx] ?? `Regime ${idx + 1}`;
  }

  if (scenarioSetKey === "env-fullrange-v1") {
    if (idx === 0) return "Full Range";
    return `Window ${idx + 1}`;
  }

  const code = windowCode(idx);
  if (t) {
    const translated = t(`windows.${code}.title`);
    if (translated !== `windows.${code}.title`) return translated;
  }
  return storyCards[code]?.title ?? `Window ${idx + 1}`;
}

function curvePoints(ret: number | null | undefined) {
  const change = ret ?? 0;
  const anchors = [0, 0.1, 0.28, 0.18, 0.48, 0.63, 0.84, 1];
  const wobble = [0, -0.7, 0.5, -0.35, 0.6, -0.25, 0.35, 0];
  const scale = Math.min(1.8, Math.max(0.45, Math.abs(change) / 6));
  return anchors.map((anchor, index) =>
    Number((100 + change * anchor + wobble[index] * scale).toFixed(1)),
  );
}

type WindowSlot = {
  index: number;
  code: string;
  label: string;
  run: ArenaScenarioRunOut | null;
  reportWindow: ArenaSubmissionReportWindow | null;
};

type WindowModalProps = {
  slot: WindowSlot | null;
  submission: ArenaSubmissionDetailOut | null;
  onClose: () => void;
};

function WindowDetailModal({ slot, submission, onClose }: WindowModalProps) {
  const { t } = useTranslation("arena");
  const isOpen = !!slot && !!submission;
  const { panelRef } = useModalA11y(isOpen, onClose);
  const titleId = React.useId();

  if (!slot || !submission) return null;

  const run = slot.run;
  const breakdown = slot.reportWindow?.breakdown ?? null;
  const story = storyCards[slot.code] ?? null;
  const tone = statusMark(run?.status ?? "pending", run?.return_pct);
  const curve = curvePoints(run?.return_pct);
  const coachingSections = breakdown
    ? [
        { title: t("modal.whatWorked"), items: breakdown.what_worked },
        { title: t("modal.whatDidnt"), items: breakdown.what_didnt_work },
        { title: t("modal.improveNext"), items: breakdown.improvement_areas },
      ]
    : [];

  const curveMin = Math.min(...curve);
  const curveMax = Math.max(...curve);
  const curveSpan = Math.max(1e-9, curveMax - curveMin);
  const chartTop = 24;
  const chartBottom = 200;
  const chartHeight = chartBottom - chartTop;
  const normalizeY = (v: number) =>
    chartBottom - ((v - curveMin) / curveSpan) * chartHeight;

  const path = curve
    .map((value, index) => {
      const x = (index / (curve.length - 1)) * 580 + 10;
      const y = normalizeY(value);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");

  const area = `M 10 ${chartBottom} ${curve
    .map((value, index) => {
      const x = (index / (curve.length - 1)) * 580 + 10;
      const y = normalizeY(value);
      return `L ${x} ${y}`;
    })
    .join(" ")} L 590 ${chartBottom} Z`;

  const notes = [
    {
      title: t("modal.windowOpens"),
      badge: fmtShort(run?.window_start ?? null),
      copy: `${slot.label} starts on ${pairName(submission.market_id)} under ${submission.scenario_set_key}.`,
      tone: "flat",
    },
    {
      title: run?.status === "finished" ? t("modal.executionClosed") : t("modal.executionStatus"),
      badge: (run?.status ?? "pending").toUpperCase(),
      copy:
        run?.status === "finished"
          ? `The replay window completed with ${pct(run.return_pct)} return.`
          : `This window is still ${run?.status ?? "pending"} and will refresh automatically.`,
      tone:
        run?.return_pct == null ? "flat" : run.return_pct >= 0 ? "win" : "loss",
    },
    {
      title: t("modal.replayLink"),
      badge: run ? `${run.run_id.slice(0, 8)}…` : "N/A",
      copy:
        submission.visibility === "private"
          ? t("modal.replayHidden")
          : run
            ? t("modal.openReplay")
            : t("modal.replayNotCreated"),
      tone: "flat",
    },
  ] as const;

  return (
    <div className="event-modal" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby={titleId}>
      <article className="event-modal-panel" onClick={(e) => e.stopPropagation()} ref={panelRef as React.RefObject<HTMLElement>}>
        <header className="event-modal-head">
          <div className="modal-head-main">
            <div className="modal-head-title-row">
              <span className="event-code-chip">{slot.code}</span>
              <h3 id={titleId}>{story ? t(`windows.${slot.code}.title`, { defaultValue: story.title }) : slot.label}</h3>
            </div>
            <p>
              {story
                ? t(`windows.${slot.code}.subtitle`, { defaultValue: story.subtitle })
                : `${pairName(submission.market_id)} · ${submission.scenario_set_key} · ${fmt(run?.window_start ?? null)} to ${fmt(run?.window_end ?? null)}`}
            </p>
          </div>
          <div className="modal-tag-row">
            {story ? (
              <>
                <span className="modal-tag tone-strong">{t("modal.difficulty")}: {t(`windows.${slot.code}.difficulty`, { defaultValue: story.difficulty })}</span>
                <span className="modal-tag tone-avg">{t("modal.regime")}: {t(`windows.${slot.code}.regime`, { defaultValue: story.regime })}</span>
                <span className={`modal-tag ${story.edge === "Strong" ? "tone-strong" : story.edge === "Weak" ? "tone-weak" : "tone-avg"}`}>
                  {t("modal.edge")}: {t(`windows.${slot.code}.edge`, { defaultValue: story.edge })}
                </span>
              </>
            ) : (
              <>
                <span className="modal-tag">{(run?.status ?? "pending").toUpperCase()}</span>
                <span className={`modal-tag ${tone === "strong" ? "tone-strong" : tone === "weak" || tone === "crash" ? "tone-weak" : "tone-avg"}`}>
                  {t("modal.return")}: {pct(run?.return_pct)}
                </span>
                <span className="modal-tag">Run: {run ? `${run.run_id.slice(0, 8)}…` : "pending"}</span>
              </>
            )}
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            {t("modal.escClose")}
          </button>
        </header>

        <div className="event-modal-body">
          <section className="event-modal-left">
            <div className="modal-card story-card">
              <h4>{story ? t("modal.storyline") : t("modal.windowOverview")}</h4>
              <p className="story-subtitle">{story ? `${t(`windows.${slot.code}.title`, { defaultValue: story.title })} · ${story.period}` : slot.label}</p>
              <p style={{ fontSize: "14px", lineHeight: 1.5 }}>
                {story
                  ? t(`windows.${slot.code}.background`, { defaultValue: story.background })
                  : t("modal.defaultWindowDescription", { defaultValue: "This trial window ran with the exact same prompt, market, and model configuration as the rest of the submission. Use it to compare how the strategy behaved from one historical slice to the next." })}
              </p>
            </div>

            <div className="modal-card">
              <div className="modal-card-head">
                <h4>{t("modal.windowCurve")}</h4>
                <span>{pct(run?.return_pct)}</span>
              </div>
              <div className="curve-meta-strip">
                <span>{t("submission.pair")}: {pairName(submission.market_id)}</span>
                <span>{t("submission.status")}: {(run?.status ?? "pending").toUpperCase()}</span>
                <span>Submission: {submission.submission_id.slice(0, 8)}…</span>
              </div>

              <svg
                viewBox="0 0 600 220"
                className="modal-curve-svg"
                preserveAspectRatio="none"
                style={{ height: "200px" }}
              >
                <g className="chart-grid">
                  <line x1="0" y1={chartTop + chartHeight * 0.25} x2="600" y2={chartTop + chartHeight * 0.25} />
                  <line x1="0" y1={chartTop + chartHeight * 0.5} x2="600" y2={chartTop + chartHeight * 0.5} />
                  <line x1="0" y1={chartTop + chartHeight * 0.75} x2="600" y2={chartTop + chartHeight * 0.75} />
                </g>
                <path className={`modal-curve-area ${run?.return_pct != null && run.return_pct < 0 ? "neg" : "pos"}`} d={area} />
                <path className={`modal-curve-line ${run?.return_pct != null && run.return_pct < 0 ? "neg" : "pos"}`} d={path} />
                {curve.map((value, index) => {
                  const x = (index / (curve.length - 1)) * 580 + 10;
                  return <circle key={`${slot.code}-${index}`} cx={x} cy={normalizeY(value)} r="4" className="modal-dot base-dot" />;
                })}
              </svg>
            </div>
          </section>

          <section className="event-modal-right">
            <div className="modal-card">
              <h4>{t("modal.windowStats")}</h4>
              <div className="modal-stat-grid">
                <div className="stat-box" data-tone={tone === "strong" ? "strong" : tone === "weak" || tone === "crash" ? "weak" : "neutral"}>
                  <span>{t("modal.return")}</span>
                  <strong>{pct(run?.return_pct)}</strong>
                </div>
                <div className="stat-box" data-tone="neutral">
                  <span>{t("submission.status").toUpperCase()}</span>
                  <strong>{(run?.status ?? "pending").toUpperCase()}</strong>
                </div>
                <div className="stat-box" data-tone="neutral">
                  <span>{t("detail.start")}</span>
                  <strong>{fmtShort(run?.window_start ?? null)}</strong>
                </div>
                <div className="stat-box" data-tone="neutral">
                  <span>{t("detail.end")}</span>
                  <strong>{fmtShort(run?.window_end ?? null)}</strong>
                </div>
                <div className="stat-box" data-tone="neutral">
                  <span>RUN ID</span>
                  <strong>{run ? `${run.run_id.slice(0, 8)}…` : "–"}</strong>
                </div>
              </div>
            </div>

            <div className="modal-card nodes-card">
              <h4>{t("modal.executionNotes")}</h4>
              <ul className="modal-node-list">
                {notes.map((note) => (
                  <li key={note.title} className={`node-card ${note.tone}`}>
                    <div className="node-dot" />
                    <div className="node-content">
                      <div className="node-top">
                        <strong>{note.title}</strong>
                        <em>{note.badge}</em>
                      </div>
                      <p>{note.copy}</p>
                    </div>
                  </li>
                ))}
              </ul>

              {submission.visibility !== "private" && run ? (
                <Link to={`/runs/${run.run_id}`} className="leaderboard-entry-link" style={{ marginTop: "12px" }}>
                  {t("modal.openReplayBtn")}
                </Link>
              ) : null}
            </div>

            <div className="modal-card">
              <div className="modal-card-head">
                <h4>{t("detail.windowCoaching")}</h4>
                <span>{breakdown ? t("modal.importedBreakdown") : t("modal.notGenerated")}</span>
              </div>

              {breakdown ? (
                <>
                  <p className="story-subtitle">{breakdown.key_takeaway}</p>
                  <p style={{ fontSize: "14px", lineHeight: 1.6, color: "#3b3b3b" }}>{breakdown.window_story}</p>
                  <div style={{ display: "grid", gap: "12px", marginTop: "16px" }}>
                    {coachingSections.map((section) => (
                      <div key={section.title} className="lb-rule-box" style={{ marginTop: 0 }}>
                        <strong>{section.title}</strong>
                        {section.items.map((item) => (
                          <span key={item}>- {item}</span>
                        ))}
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p style={{ fontSize: "14px", lineHeight: 1.6, color: "#555" }}>
                  {t("modal.noBreakdownYet")}
                </p>
              )}
            </div>
          </section>
        </div>
      </article>
    </div>
  );
}

export default function SubmissionDetailPage() {
  const { t } = useTranslation("arena");
  const submissionId = useParams<{ submissionId: string }>().submissionId ?? "";

  const [data, setData] = React.useState<ArenaSubmissionDetailOut | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedCode, setSelectedCode] = React.useState<string | null>(null);
  const [highlightedCode, setHighlightedCode] = React.useState<string | null>(null);

  const detailPersistence = useTourPersistence("submission-detail-v1");
  const detailTour = useProductTour(submissionDetailSteps);
  const { activeTour, stopTour } = useTourContext();

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiJson<ArenaSubmissionDetailOut>(`/arena/submissions/${submissionId}`);
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

  const shouldRefresh =
    !data?.status || data.status === "pending" || data.status === "submitted" || data.status === "running";
  useRealtimeRefresh({
    wsPath: "/runs/ws",
    enabled: shouldRefresh,
    pollIntervalMs: 2500,
    refresh,
  });

  React.useEffect(() => {
    if (data && !detailPersistence.hasCompleted()) {
      const timeoutId = window.setTimeout(() => {
        detailTour.start();
        detailPersistence.markCompleted();
      }, 600);
      return () => window.clearTimeout(timeoutId);
    }
  }, [data]); // eslint-disable-line react-hooks/exhaustive-deps

  React.useEffect(() => {
    if (activeTour === "submission-detail-v1") {
      detailTour.start();
      stopTour();
    }
  }, [activeTour]); // eslint-disable-line react-hooks/exhaustive-deps

  const report = data?.report_json ?? null;
  const slots = React.useMemo<WindowSlot[]>(() => {
    const total = data?.windows_total ?? data?.runs.length ?? 0;
    const runs = [...(data?.runs ?? [])].sort((a, b) => a.scenario_index - b.scenario_index);
    const byIndex = new Map(runs.map((run) => [run.scenario_index, run]));
    const reportByIndex = new Map((report?.windows ?? []).map((window) => [window.scenario_index, window]));
    return Array.from({ length: total }, (_, index) => ({
      index,
      code: windowCode(index),
      label: windowLabel(data?.scenario_set_key, index, t),
      run: byIndex.get(index) ?? null,
      reportWindow: reportByIndex.get(index) ?? null,
    }));
  }, [data, report?.windows, t]);

  const finishedSlots = React.useMemo(
    () =>
      slots.filter(
        (slot) => slot.run?.status === "finished" && slot.run.return_pct != null && !Number.isNaN(slot.run.return_pct),
      ),
    [slots],
  );

  const positiveSlots = finishedSlots.filter((slot) => (slot.run?.return_pct ?? 0) >= 0);
  const winRatePct = finishedSlots.length > 0 ? (positiveSlots.length / finishedSlots.length) * 100 : null;
  const bestSlot = finishedSlots.reduce<WindowSlot | null>((best, current) => {
    if (!best) return current;
    return (current.run?.return_pct ?? -Infinity) > (best.run?.return_pct ?? -Infinity) ? current : best;
  }, null);
  const worstSlot = finishedSlots.reduce<WindowSlot | null>((worst, current) => {
    if (!worst) return current;
    return (current.run?.return_pct ?? Infinity) < (worst.run?.return_pct ?? Infinity) ? current : worst;
  }, null);

  const progressPct =
    data && data.windows_total > 0 ? (data.windows_completed / data.windows_total) * 100 : 0;
  const score = report?.overall_score ?? fallbackScoreValue(data?.total_return_pct ?? null, winRatePct, progressPct);
  const progressText = data ? `${data.windows_completed}/${data.windows_total}` : "…";
  const statusDisplay = getSubmissionStatusDisplay({
    status: data?.status,
    startedAt: data?.started_at,
  });

  const summary = React.useMemo(() => {
    if (!data) return "Loading trial report.";
    if (report?.overview) return report.overview;

    if (statusDisplay.isQueued) {
      return `This trial is in the queue for ${pairName(data.market_id)}. Nothing has started yet, and the report will refresh automatically the moment a worker begins replaying the submission.`;
    }

    if (data.status === "pending" || data.status === "running") {
      return `This trial is still executing on ${pairName(data.market_id)}. ${data.windows_completed} of ${data.windows_total} windows have completed so far, and the report will keep refreshing until the full submission settles.`;
    }

    if (!finishedSlots.length) {
      return `This trial has no finished windows yet. Once the replay windows complete, the report will summarize relative performance, best and worst slices, and direct links into each replay run.`;
    }

    const bestCopy = bestSlot?.run?.return_pct != null ? `${bestSlot.code} ${pct(bestSlot.run.return_pct)}` : "–";
    const worstCopy = worstSlot?.run?.return_pct != null ? `${worstSlot.code} ${pct(worstSlot.run.return_pct)}` : "–";

    return `The submission finished ${finishedSlots.length} windows on ${pairName(data.market_id)} with ${pct(data.total_return_pct)} total return and ${pct(data.avg_return_pct)} average return per window. Best slice: ${bestCopy}. Weakest slice: ${worstCopy}.`;
  }, [bestSlot, data, finishedSlots.length, report?.overview, statusDisplay.isQueued, worstSlot]);

  const chartMax = React.useMemo(() => {
    const values = slots
      .map((slot) => Math.abs(slot.run?.return_pct ?? 0))
      .filter((value) => Number.isFinite(value));
    return Math.max(5, ...values, Math.abs(data?.total_return_pct ?? 0));
  }, [data?.total_return_pct, slots]);

  const selectedSlot = slots.find((slot) => slot.code === selectedCode) ?? null;
  const featuredBreakdownSlot =
    selectedSlot?.reportWindow?.breakdown
      ? selectedSlot
      : bestSlot?.reportWindow?.breakdown
        ? bestSlot
        : slots.find((slot) => slot.reportWindow?.breakdown) ?? null;
  const featuredBreakdown = featuredBreakdownSlot?.reportWindow?.breakdown ?? null;

  return (
    <>
      <SEO title="Submission Detail" description="Arena submission results." noindex />
      <main className="layout animate-rise">
        <section className="left-column">
          <article className="hero-card block" data-tour="submission-hero-card">
            <div className="hero-meta">
              {t("detail.trialReport")} / {data?.model_key ?? "LOADING"} / {pairName(data?.market_id)} / {fmt(data?.created_at)}
            </div>
            <div className="hero-title-row">
              <div className="score">
                <div className="score-label">{t("detail.trialScore")}</div>
                <div className="score-value">{String(score).padStart(2, "0")}</div>
              </div>
              <div className="persona">
                <h1>
                  {data?.status === "finished"
                    ? report?.archetype ?? t("detail.historicalTrialVerdict")
                    : statusDisplay.headline}
                </h1>
                {report?.representative ? (
                  <p className="representative">{t("detail.archetype")}: {report.representative}</p>
                ) : null}
                <p>
                  {t("submission.status")}: <span data-testid="tournament-run-status">{statusDisplay.label}</span> · {t("submission.progress")}:{" "}
                  <span data-testid="tournament-run-progress">{progressText}</span> · {t("submission.pair")}: {pairName(data?.market_id)}
                </p>
                <div className="tags">
                  <span>{data?.scenario_set_key ?? "scenario-set"}</span>
                  <span>{pairName(data?.market_id)}</span>
                  <span>{data?.visibility ?? "public"}</span>
                  <span>{statusDisplay.label}</span>
                  {report ? <span>{report.generation_mode}</span> : null}
                </div>
              </div>
            </div>
            <p className="hero-summary">{summary}</p>
            {error ? <p className="hero-meta" style={{ color: "var(--red)" }}>{error}</p> : null}
          </article>

          {shouldRefresh ? (
            <section className="block">
              <div className="hero-meta">{t("detail.runProgress")}</div>
              <div className="mt-3 h-3 w-full overflow-hidden border-2 border-[#2f2f2f] bg-[#f2f2f2]">
                <div
                  className="h-full bg-[#3b66d9] transition-[width] duration-300"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <p className="mt-3 mb-0 text-[16px] text-[#555]">
                {statusDisplay.isQueued
                  ? t("detail.queueMessage")
                  : t("detail.autoRefreshMessage")}
              </p>
            </section>
          ) : null}

          <section className="metric-grid" data-tour="submission-metric-grid">
            <article className="metric block">
              <h3>{t("detail.totalReturn")}</h3>
              <p className={`value ${pctTone(data?.total_return_pct)}`}>{pct(data?.total_return_pct)}</p>
              <p className="rank good">{t("detail.submissionLevel")}</p>
            </article>
            <article className="metric block">
              <h3>{t("detail.avgWindow")}</h3>
              <p className={`value ${pctTone(data?.avg_return_pct)}`}>{pct(data?.avg_return_pct)}</p>
              <p className="rank elite">{t("detail.perWindowAvg")}</p>
            </article>
            <article className="metric block">
              <h3>{t("detail.winRate")}</h3>
              <p className="value neutral">{winRatePct == null ? "–" : `${winRatePct.toFixed(1)}%`}</p>
              <p className="rank mid">{finishedSlots.length} {t("detail.finishedWindows")}</p>
            </article>
            <article className="metric block">
              <h3>{t("detail.bestWindow")}</h3>
              <p className={`value ${pctTone(bestSlot?.run?.return_pct)}`}>{bestSlot ? bestSlot.code : "–"}</p>
              <p className="rank good">{report?.best_window?.reason ?? (bestSlot ? pct(bestSlot.run?.return_pct) : t("detail.noCompletedWindow"))}</p>
            </article>
            <article className="metric block">
              <h3>{t("detail.worstWindow")}</h3>
              <p className={`value ${pctTone(worstSlot?.run?.return_pct)}`}>{worstSlot ? worstSlot.code : "–"}</p>
              <p className="rank bad">{report?.worst_window?.reason ?? (worstSlot ? pct(worstSlot.run?.return_pct) : t("detail.noCompletedWindow"))}</p>
            </article>
          </section>

          {report ? (
            <div data-tour="submission-report">
              {report.roast ? (
                <section className="block" style={{ borderLeft: "4px solid var(--red, #d44)", paddingLeft: "16px" }}>
                  <div className="hero-meta">{t("detail.theRoast")}</div>
                  <p className="mt-3 text-[17px] italic leading-8 text-[#333]">&ldquo;{report.roast}&rdquo;</p>
                </section>
              ) : null}
              <section className="grid gap-4 xl:grid-cols-3">
                <article className="block">
                  <div className="hero-meta">{t("detail.strengths")}</div>
                  <ul className="mt-4 space-y-3 text-[15px] leading-7 text-[#444]">
                    {report.strengths.map((item) => (
                      <li key={item}>- {item}</li>
                    ))}
                  </ul>
                </article>
                <article className="block">
                  <div className="hero-meta">{t("detail.weaknesses")}</div>
                  <ul className="mt-4 space-y-3 text-[15px] leading-7 text-[#444]">
                    {report.weaknesses.map((item) => (
                      <li key={item}>- {item}</li>
                    ))}
                  </ul>
                </article>
                <article className="block">
                  <div className="hero-meta">{t("detail.nextActions")}</div>
                  <ul className="mt-4 space-y-3 text-[15px] leading-7 text-[#444]">
                    {report.recommendations.map((item) => (
                      <li key={item}>- {item}</li>
                    ))}
                  </ul>
                </article>
              </section>
            </div>
          ) : null}

          <section className="viz-grid">
            <article className="block chart-card" data-tour="submission-returns-chart">
              <header>
                <h2>{t("detail.windowReturns")}</h2>
                <span>
                  {data?.model_key ?? "…"} · {pairName(data?.market_id)} · {data?.scenario_set_key ?? "scenario-set"}
                </span>
              </header>
              <svg viewBox="0 0 640 260" className="bar-chart" aria-label="trial-window-returns">
                <rect x="0" y="0" width="640" height="260" fill="#f7f7f5" />
                <line x1="30" y1="30" x2="30" y2="234" className="axis-line" />
                <line x1="30" y1="234" x2="624" y2="234" className="axis-line" />
                <line x1="30" y1="130" x2="624" y2="130" className="zero-line" />

                <text x="6" y="35" className="y-tick">
                  +{chartMax.toFixed(0)}%
                </text>
                <text x="10" y="134" className="y-tick">
                  0%
                </text>
                <text x="6" y="230" className="y-tick">
                  -{chartMax.toFixed(0)}%
                </text>

                {slots.map((slot, index) => {
                  const value = slot.run?.return_pct ?? 0;
                  const height = Math.abs(value / chartMax) * 96;
                  const x = 44 + index * 58;
                  const y = value >= 0 ? 130 - height : 130;
                  const dimmed = highlightedCode && highlightedCode !== slot.code;
                  const pending = !slot.run || slot.run.return_pct == null;

                  return (
                    <g
                      key={slot.code}
                      className={dimmed ? "bar-item dim" : "bar-item"}
                      onMouseEnter={() => setHighlightedCode(slot.code)}
                      onMouseLeave={() => setHighlightedCode(null)}
                      onClick={() => slot.run ? setSelectedCode(slot.code) : null}
                      style={{ cursor: slot.run ? "pointer" : "default" }}
                    >
                      <rect
                        x={x}
                        y={pending ? 126 : y}
                        width="42"
                        height={pending ? 8 : Math.max(4, height)}
                        className={pending || value >= 0 ? "bar-pos" : "bar-neg"}
                        style={pending ? { fill: "#b9b9b9" } : undefined}
                      />
                      <text x={x + 2} y={pending || value < 0 ? 146 + Math.max(0, height) : y - 8} className="bar-value">
                        {pending ? "…" : pct(value)}
                      </text>
                      <text x={x + 5} y="250" className="bar-label">
                        {slot.code}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </article>

            <article className="block chart-card">
              <header>
                <h2>{t("detail.trialBreakdown")}</h2>
                <span>{progressText} {t("detail.complete")}</span>
              </header>
              <div className="lb-selected-stat-grid">
                <div className="lb-selected-stat">
                  <span>{t("detail.submissionId")}</span>
                  <strong>{submissionId.slice(0, 8)}…</strong>
                </div>
                <div className="lb-selected-stat">
                  <span>{t("submission.status")}</span>
                  <strong>{(data?.status ?? "pending").toUpperCase()}</strong>
                </div>
                <div className="lb-selected-stat">
                  <span>{t("detail.created")}</span>
                  <strong>{fmtShort(data?.created_at)}</strong>
                </div>
                <div className="lb-selected-stat">
                  <span>{t("detail.updated")}</span>
                  <strong>{fmtShort(data?.updated_at)}</strong>
                </div>
                <div className="lb-selected-stat">
                  <span>{t("submission.pair")}</span>
                  <strong>{pairName(data?.market_id)}</strong>
                </div>
                <div className="lb-selected-stat">
                  <span>{t("detail.visibility")}</span>
                  <strong>{(data?.visibility ?? "public").toUpperCase()}</strong>
                </div>
              </div>

              <div className="lb-rule-box" style={{ marginTop: "12px" }}>
                <strong>{t("detail.readingTheTrial")}</strong>
                <span>{t("detail.readingStep1")}</span>
                <span>{t("detail.readingStep2")}</span>
                <span>{t("detail.readingStep3")}</span>
              </div>

              {featuredBreakdown ? (
                <div className="lb-rule-box" style={{ marginTop: "16px" }}>
                  <strong>
                    {t("detail.windowCoaching")} / {featuredBreakdownSlot?.code ?? "Window"}
                  </strong>
                  <span>{featuredBreakdown.key_takeaway}</span>
                  <span>{featuredBreakdown.window_story}</span>
                  {featuredBreakdown.what_worked.slice(0, 2).map((item) => (
                    <span key={item}>Worked: {item}</span>
                  ))}
                </div>
              ) : null}
            </article>
          </section>

          <article className="leaderboard-entry block">
            <p>
              {t("detail.useReport")}
            </p>
            <div className="entry-links">
              <Link to="/arena" className="return-trials-btn">
                {t("detail.returnToTrials")}
              </Link>
              <Link to="/leaderboard" className="mini-leaderboard-btn">
                {t("detail.openLeaderboard")}
              </Link>
              {data?.visibility !== "private" && bestSlot?.run ? (
                <Link to={`/runs/${bestSlot.run.run_id}`} className="mini-leaderboard-btn trials-link">
                  {t("detail.bestWindowLink")}
                </Link>
              ) : null}
              <button type="button" onClick={refresh} className="mini-leaderboard-btn">
                {loading ? t("detail.refreshing") : t("detail.refresh")}
              </button>
            </div>
          </article>
        </section>

        <aside className="right-column">
          <section className="heatlog-panel" data-tour="submission-heatlog">
            <header className="heatlog-header">
              <div>{t("detail.windowPerformance")}</div>
            </header>

            <div className="heatlog-col-head">
              <span>{t("detail.event")}</span>
              <span>{t("detail.returnPct")}</span>
              <span>{t("submission.status").toUpperCase()}</span>
              <span>{t("detail.start")}</span>
              <span>{t("detail.end")}</span>
              <span>{t("detail.run")}</span>
            </div>

            {slots.map((slot) => {
              const run = slot.run;
              const mark = statusMark(run?.status ?? "pending", run?.return_pct);
              const isActive = selectedCode === slot.code;
              const isHighlighted = highlightedCode === slot.code;

              return (
                <article
                  key={slot.code}
                  className={`heatlog-row ${isActive ? "is-active" : ""}`}
                  data-tour={slot.index === 0 ? "submission-window-row" : undefined}
                  role="button"
                  tabIndex={0}
                  onClick={() => run ? setSelectedCode(slot.code) : null}
                  onMouseEnter={() => setHighlightedCode(slot.code)}
                  onMouseLeave={() => setHighlightedCode(null)}
                  style={{
                    outline: isHighlighted && !isActive ? "2px solid #a0a0a0" : undefined,
                    outlineOffset: isHighlighted && !isActive ? "-2px" : undefined,
                    cursor: run ? "pointer" : "default",
                  }}
                >
                  <div className="event-cell">
                    <span className={`event-mark ${mark}`}>
                      {mark === "warn" ? "!" : mark === "crash" ? "X" : ""}
                    </span>
                    <div>
                      <strong>{slot.code}</strong>
                      <p>{slot.label}</p>
                    </div>
                  </div>
                  <div className={`metric-cell ${mark === "strong" ? "strong" : mark === "avg" ? "avg" : mark === "weak" ? "weak" : ""}`}>
                    {pct(run?.return_pct)}
                  </div>
                  <div className={`metric-cell ${statusCellClass(run?.status ?? "pending")}`}>
                    {(run?.status ?? "pending").toUpperCase()}
                  </div>
                  <div className="trades-cell">{fmtShort(run?.window_start ?? null)}</div>
                  <div className="trades-cell">{fmtShort(run?.window_end ?? null)}</div>
                  <div className="trades-cell">
                    {run && data?.visibility !== "private" ? (
                      <Link
                        to={`/runs/${run.run_id}`}
                        onClick={(e) => e.stopPropagation()}
                        style={{ textDecoration: "none", color: "inherit" }}
                      >
                        →
                      </Link>
                    ) : (
                      "–"
                    )}
                  </div>
                </article>
              );
            })}

            {slots.length === 0 ? (
              <div className="p-6 text-center text-[#666]">{t("detail.noScenarioWindows")}</div>
            ) : null}

            <footer className="heatlog-legend">
              <span>
                <i className="lg strong"></i>{t("detail.strong")}
              </span>
              <span>
                <i className="lg avg"></i>{t("detail.inProgress")}
              </span>
              <span>
                <i className="lg weak"></i>{t("detail.weak")}
              </span>
            </footer>
          </section>
        </aside>
      </main>

      <WindowDetailModal slot={selectedSlot} submission={data} onClose={() => setSelectedCode(null)} />
    </>
  );
}
