import * as React from "react";

import {
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
  statusHeadline: string;
  statusDetail: string;
  isQueued: boolean;
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
  statusHeadline,
  statusDetail,
  isQueued,
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
  const [showButton, setShowButton] = React.useState(false);

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
    const timer = window.setTimeout(() => setShowButton(true), 500);
    onReadyToNavigate?.();
    return () => window.clearTimeout(timer);
  }, [copyVisible, displayStageIndex, isTerminal, onReadyToNavigate]);

  const activeStage = loadingStages[displayStageIndex];
  const displayProgress = Math.max(activeStage.progress_percent, progressPercent);
  const trimmedPrompt = promptText.trim();
  const promptPreview =
    trimmedPrompt.length > 140 ? `${trimmedPrompt.slice(0, 137).trimEnd()}...` : trimmedPrompt;

  return (
    <main className="fixed inset-0 z-[70] flex flex-col items-center justify-center bg-[#0a0a0a] px-6">
      <p
        className="mb-6 text-[11px] uppercase tracking-[0.3em] text-[#ababab] transition-opacity duration-300"
        style={{ opacity: copyVisible ? 1 : 0 }}
      >
        {isQueued ? "QUEUED" : activeStage.label}
      </p>

      <p
        className="mb-10 max-w-md text-center text-[16px] italic leading-relaxed text-white transition-opacity duration-300 md:text-[20px]"
        style={{ opacity: copyVisible ? 1 : 0 }}
      >
        &ldquo;{currentMeme}&rdquo;
      </p>

      <div className="mb-4 h-[2px] w-full max-w-sm bg-white/10">
        <div
          className="h-full bg-white transition-all duration-500 ease-out"
          style={{ width: `${displayProgress.toFixed(0)}%` }}
        />
      </div>

      <p className="text-[10px] uppercase tracking-widest text-[#ababab]">
        {Math.round(displayProgress)}%
      </p>

      <div className="mt-6 w-full max-w-2xl border border-white/10 bg-white/5 px-5 py-4 text-white/80 backdrop-blur-sm">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] uppercase tracking-[0.24em] text-[#c7c7c7]">
          <span>{statusHeadline}</span>
          <span>Trial {submissionId.slice(0, 8)}</span>
          <span>{windowsCompleted}/{windowsTotal || 0} windows</span>
        </div>
        <p className="mt-3 text-sm leading-6 text-white">{statusDetail}</p>
        <div className="mt-4 grid gap-3 text-xs text-[#bbbbbb] md:grid-cols-3">
          <div>
            <div className="uppercase tracking-[0.2em] text-[#7f7f7f]">Pair</div>
            <div className="mt-1 text-sm text-white">{pairLabel}</div>
          </div>
          <div>
            <div className="uppercase tracking-[0.2em] text-[#7f7f7f]">Model</div>
            <div className="mt-1 break-all text-sm text-white">{modelKey}</div>
          </div>
          <div>
            <div className="uppercase tracking-[0.2em] text-[#7f7f7f]">Status</div>
            <div className="mt-1 text-sm text-white">{status ?? "pending"}</div>
          </div>
        </div>
        <p className="mt-4 border-t border-white/10 pt-4 text-xs leading-6 text-[#9f9f9f]">
          Prompt preview: {promptPreview || "Waiting for prompt details."}
        </p>
      </div>

      {error ? (
        <p className="mt-6 max-w-sm text-center text-[12px] leading-relaxed text-[#ff9b8a]">
          {error}
        </p>
      ) : null}

      {showButton ? (
        <button
          type="button"
          onClick={onViewReport}
          className="mt-10 border-2 border-white bg-transparent px-10 py-4 text-[18px] uppercase tracking-[2px] text-white transition-all duration-150 animate-landing-fade-in-up hover:bg-white hover:text-[#0a0a0a]"
        >
          View Report →
        </button>
      ) : null}
    </main>
  );
}
