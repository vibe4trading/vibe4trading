"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";

import { SubmissionLoadingScreen } from "@/app/components/SubmissionLoadingScreen";
import { useRealtimeRefresh } from "@/app/lib/realtime";
import {
  clearSubmissionLoadingSnapshot,
  readSubmissionLoadingSnapshot,
  SubmissionLoadingSnapshot,
} from "@/app/lib/submissionLoading";
import { apiJson, ArenaSubmissionDetailOut } from "@/app/lib/v4t";

const TERMINAL_STATUSES = new Set(["finished", "failed", "cancelled"]);

function pairName(marketId: string | null | undefined) {
  if (!marketId) return "Awaiting pair";
  const parts = marketId.split(":");
  return parts[parts.length - 1] ?? marketId;
}

function isTerminalStatus(status: string | null | undefined) {
  return status ? TERMINAL_STATUSES.has(status.toLowerCase()) : false;
}

export default function SubmissionLoadingPage() {
  const params = useParams<{ submissionId: string }>();
  const router = useRouter();
  const submissionId = params.submissionId;

  const [data, setData] = React.useState<ArenaSubmissionDetailOut | null>(null);
  const [snapshot, setSnapshot] = React.useState<SubmissionLoadingSnapshot | null>(null);
  const [initialLoading, setInitialLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [reportReady, setReportReady] = React.useState(false);

  const viewReport = React.useCallback(() => {
    clearSubmissionLoadingSnapshot(submissionId);
    router.replace(`/arena/submissions/${submissionId}`);
  }, [router, submissionId]);

  const refresh = React.useCallback(async () => {
    try {
      const res = await apiJson<ArenaSubmissionDetailOut>(`/arena/submissions/${submissionId}`);
      setData(res);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load submission.");
    } finally {
      setInitialLoading(false);
    }
  }, [submissionId]);

  const handleReadyToNavigate = React.useCallback(() => {
    setReportReady(true);
  }, []);

  React.useEffect(() => {
    setSnapshot(readSubmissionLoadingSnapshot(submissionId));
  }, [submissionId]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const isTerminal = isTerminalStatus(data?.status ?? null);
  useRealtimeRefresh({
    wsPath: isTerminal ? null : "/runs/ws",
    enabled: !isTerminal,
    pollIntervalMs: 2500,
    refresh,
  });

  React.useEffect(() => {
    if (!reportReady) return;
    const timeoutId = window.setTimeout(() => {
      viewReport();
    }, 900);
    return () => window.clearTimeout(timeoutId);
  }, [reportReady, viewReport]);

  const totalLlmCalls = data ? 7 * 24 * data.windows_total : 0;
  const progressPercent =
    data && totalLlmCalls > 0
      ? Math.min((data.llm_calls_completed / totalLlmCalls) * 100, 100)
      : initialLoading
        ? 5
        : 0;

  if (error && !data && !initialLoading) {
    return (
      <main className="fixed inset-0 z-[70] flex flex-col items-center justify-center bg-[#0a0a0a] px-6">
        <p className="mb-6 text-[11px] uppercase tracking-[0.3em] text-[#ababab]">
          Connection failed
        </p>
        <p className="mb-10 max-w-md text-center text-[16px] leading-relaxed text-white md:text-[20px]">
          {error}
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => {
              void refresh();
            }}
            className="border-2 border-white bg-white px-8 py-4 text-[14px] uppercase tracking-[2px] text-[#0a0a0a] transition-all duration-150 hover:bg-transparent hover:text-white"
          >
            Retry
          </button>
          <button
            type="button"
            onClick={viewReport}
            className="border-2 border-white bg-transparent px-8 py-4 text-[14px] uppercase tracking-[2px] text-white transition-all duration-150 hover:bg-white hover:text-[#0a0a0a]"
          >
            Open report
          </button>
        </div>
      </main>
    );
  }

  return (
    <SubmissionLoadingScreen
      submissionId={submissionId}
      pairLabel={pairName(snapshot?.marketId ?? data?.market_id)}
      modelKey={snapshot?.modelKey ?? data?.model_key ?? "Awaiting model"}
      promptText={
        snapshot?.promptText ??
        "Prompt locked in. Running the strategy through the historical window set before we reveal the verdict."
      }
      progressPercent={progressPercent}
      status={data?.status ?? (initialLoading ? "submitted" : null)}
      windowsCompleted={data?.windows_completed ?? 0}
      windowsTotal={data?.windows_total ?? 0}
      isTerminal={isTerminal}
      error={error}
      onViewReport={viewReport}
      onReadyToNavigate={handleReadyToNavigate}
    />
  );
}
