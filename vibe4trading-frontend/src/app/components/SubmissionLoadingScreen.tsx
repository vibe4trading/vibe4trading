"use client";

import * as React from "react";

import {
  loadingBehavior,
  loadingStages,
  MIN_STAGE_DISPLAY_MS,
  pickRandomMeme,
  resolveLoadingStageIndex,
  TEXT_FADE_MS,
} from "@/app/lib/loadingMemes";

type SubmissionLoadingScreenProps = {
  submissionId: string;
  pairLabel: string;
  modelKey: string;
  promptText: string;
  progressPercent: number;
  status: string | null;
  windowsCompleted: number;
  windowsTotal: number;
  isTerminal: boolean;
  error?: string | null;
  onViewReport: () => void;
  onReadyToNavigate?: () => void;
};

export function SubmissionLoadingScreen({
  submissionId,
  pairLabel,
  modelKey,
  promptText,
  progressPercent,
  status,
  windowsCompleted,
  windowsTotal,
  isTerminal,
  error,
  onViewReport,
  onReadyToNavigate,
}: SubmissionLoadingScreenProps) {
  const targetStageIndex = React.useMemo(
    () => resolveLoadingStageIndex(progressPercent, isTerminal),
    [isTerminal, progressPercent],
  );

  const [displayStageIndex, setDisplayStageIndex] = React.useState(targetStageIndex);
  const [copyVisible, setCopyVisible] = React.useState(true);
  const [currentMeme, setCurrentMeme] = React.useState(() =>
    pickRandomMeme(loadingStages[targetStageIndex]),
  );

  const stageVisibleAtRef = React.useRef<number | null>(null);
  const readyNotifiedRef = React.useRef(false);

  React.useEffect(() => {
    if (stageVisibleAtRef.current === null) {
      stageVisibleAtRef.current = Date.now();
    }
  }, []);

  React.useEffect(() => {
    if (targetStageIndex <= displayStageIndex) return;

    const visibleAt = stageVisibleAtRef.current ?? Date.now();
    const elapsed = Date.now() - visibleAt;
    const waitMs = Math.max(0, MIN_STAGE_DISPLAY_MS - elapsed);

    let fadeTimer = 0;
    const stageTimer = window.setTimeout(() => {
      setCopyVisible(false);
      fadeTimer = window.setTimeout(() => {
        const nextStage = loadingStages[targetStageIndex];
        setDisplayStageIndex(targetStageIndex);
        setCurrentMeme((previousMeme) => pickRandomMeme(nextStage, previousMeme));
        setCopyVisible(true);
        stageVisibleAtRef.current = Date.now();
      }, TEXT_FADE_MS);
    }, waitMs);

    return () => {
      window.clearTimeout(stageTimer);
      if (fadeTimer) window.clearTimeout(fadeTimer);
    };
  }, [displayStageIndex, targetStageIndex]);

  React.useEffect(() => {
    const isReady = isTerminal && displayStageIndex === loadingStages.length - 1 && copyVisible;
    if (!isReady || readyNotifiedRef.current) return;
    readyNotifiedRef.current = true;
    onReadyToNavigate?.();
  }, [copyVisible, displayStageIndex, isTerminal, onReadyToNavigate]);

  const activeStage = loadingStages[displayStageIndex];
  const progressWidth = `${Math.max(activeStage.progress_percent, progressPercent).toFixed(0)}%`;
  const promptPreview = promptText.trim() || "Prompt locked in. Preparing the trial now.";
  const minimumStageSeconds = (MIN_STAGE_DISPLAY_MS / 1000).toFixed(1);

  return (
    <main className="submission-loading-shell relative min-h-screen overflow-hidden text-[#f4eee0]">
      <div className="submission-loading-orb submission-loading-orb-a" aria-hidden="true" />
      <div className="submission-loading-orb submission-loading-orb-b" aria-hidden="true" />
      <div className="submission-loading-grid" aria-hidden="true" />
      <div className="submission-loading-scan" aria-hidden="true" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col justify-center px-5 py-8 sm:px-8 lg:px-12">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 text-[11px] uppercase tracking-[0.28em] text-[#f6d77f] sm:text-[12px]">
          <span>Submission {submissionId.slice(0, 8)}</span>
          <span>{status ? `Status ${status}` : "Status syncing"}</span>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <section className="submission-loading-panel border border-[#f6d77f]/30 bg-[#07111d]/76 p-6 shadow-[0_30px_80px_rgba(0,0,0,0.45)] backdrop-blur-md sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-[12px] uppercase tracking-[0.34em] text-[#8ec5ff]">Run Uplink</p>
                <h1 className="mt-3 max-w-3xl text-[34px] uppercase leading-[0.92] tracking-[0.08em] text-[#fff4d4] sm:text-[52px]">
                  {activeStage.label}
                </h1>
              </div>
              <div className="rounded-full border border-[#f6d77f]/35 bg-[#0c1828]/90 px-4 py-2 text-[12px] uppercase tracking-[0.22em] text-[#f6d77f]">
                {windowsTotal > 0 ? `${windowsCompleted}/${windowsTotal} windows` : `${Math.round(progressPercent)}% synced`}
              </div>
            </div>

            <div className="mt-8 overflow-hidden border border-[#203450] bg-[#0b1624] p-5 sm:p-6">
              <div
                className={`transition-opacity duration-300 ${copyVisible ? "opacity-100" : "opacity-0"}`}
              >
                <p className="text-[12px] uppercase tracking-[0.3em] text-[#8ec5ff]">Live meme feed</p>
                <p className="mt-4 text-[24px] leading-[1.5] text-[#fff8ea] sm:text-[32px] sm:leading-[1.45]">
                  {currentMeme}
                </p>
              </div>
            </div>

            <div className="mt-8">
              <div className="flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.22em] text-[#a8bed8] sm:text-[12px]">
                <span>{loadingBehavior.progress_bar}</span>
                <span>{Math.round(progressPercent)}%</span>
              </div>
              <div className="mt-3 h-4 overflow-hidden rounded-full border border-[#33587c] bg-[#07111d]">
                <div
                  className="h-full rounded-full bg-[linear-gradient(90deg,#f6d77f_0%,#ff9f5c_45%,#7ed7f7_100%)] transition-[width] duration-1000 ease-out"
                  style={{ width: progressWidth }}
                />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {loadingStages.map((stage) => {
                  const isActive = stage.stage === activeStage.stage;
                  const isReached = stage.stage <= activeStage.stage;
                  return (
                    <span
                      key={stage.stage}
                      className={`border px-2 py-1 text-[10px] uppercase tracking-[0.18em] transition-colors sm:text-[11px] ${
                        isActive
                          ? "border-[#f6d77f] bg-[#f6d77f]/18 text-[#fff4d4]"
                          : isReached
                            ? "border-[#7ed7f7]/45 bg-[#7ed7f7]/10 text-[#d1f3ff]"
                            : "border-[#27405c] bg-[#09111b] text-[#5f7690]"
                      }`}
                    >
                      {stage.label}
                    </span>
                  );
                })}
              </div>
            </div>

            <div className="mt-8 grid gap-3 text-[12px] uppercase tracking-[0.18em] text-[#a8bed8] sm:grid-cols-3">
              <div className="border border-[#203450] bg-[#09111b]/88 p-4">
                <div className="text-[#6d88a6]">Pair</div>
                <div className="mt-2 text-[15px] text-[#fff4d4]">{pairLabel}</div>
              </div>
              <div className="border border-[#203450] bg-[#09111b]/88 p-4">
                <div className="text-[#6d88a6]">Model</div>
                <div className="mt-2 text-[15px] text-[#fff4d4]">{modelKey}</div>
              </div>
              <div className="border border-[#203450] bg-[#09111b]/88 p-4">
                <div className="text-[#6d88a6]">Transition</div>
                <div className="mt-2 text-[15px] text-[#fff4d4]">{loadingBehavior.text_transition}</div>
              </div>
            </div>
          </section>

          <aside className="submission-loading-panel flex flex-col gap-4 border border-[#7ed7f7]/22 bg-[#09111b]/82 p-6 shadow-[0_24px_70px_rgba(0,0,0,0.38)] backdrop-blur-md sm:p-8">
            <div>
              <p className="text-[12px] uppercase tracking-[0.3em] text-[#7ed7f7]">Prompt lockbox</p>
              <div className="mt-4 border border-[#203450] bg-[#050b13] p-4 text-[14px] leading-7 text-[#d5dfec]">
                {promptPreview}
              </div>
            </div>

            <div className="grid gap-3 text-[12px] uppercase tracking-[0.18em] text-[#a8bed8]">
              <div className="border border-[#203450] bg-[#07111d]/88 p-4">
                <div className="text-[#6d88a6]">Backend sync</div>
                <div className="mt-2 text-[15px] text-[#fff4d4]">
                  {windowsTotal > 0
                    ? `${windowsCompleted} of ${windowsTotal} replay windows complete`
                    : "Waiting for submission telemetry"}
                </div>
              </div>
              <div className="border border-[#203450] bg-[#07111d]/88 p-4">
                <div className="text-[#6d88a6]">Stage pacing</div>
                <div className="mt-2 text-[15px] text-[#fff4d4]">
                  Minimum {minimumStageSeconds}s per displayed stage
                </div>
              </div>
              {error ? (
                <div className="border border-[#b86048] bg-[#35130d] p-4 text-[#ffd6c9]">
                  <div className="text-[#ffb39b]">Connection warning</div>
                  <div className="mt-2 text-[14px] normal-case tracking-normal">{error}</div>
                </div>
              ) : null}
            </div>

            <div className="mt-auto flex flex-col gap-3 pt-4">
              <button
                type="button"
                onClick={onViewReport}
                className={`border px-5 py-4 text-[12px] uppercase tracking-[0.26em] transition-all ${
                  isTerminal
                    ? "border-[#f6d77f] bg-[#f6d77f] text-[#09111b] opacity-100"
                    : "border-[#33587c] bg-[#0b1624] text-[#6d88a6] opacity-55"
                }`}
                disabled={!isTerminal}
              >
                {isTerminal ? "View report" : "Waiting for completion"}
              </button>
              <p className="text-[11px] uppercase tracking-[0.18em] text-[#6d88a6]">
                {isTerminal ? "Report ready. Redirecting now." : loadingBehavior.on_complete}
              </p>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
