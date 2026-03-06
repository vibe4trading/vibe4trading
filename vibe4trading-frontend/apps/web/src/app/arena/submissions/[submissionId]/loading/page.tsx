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

  const progressPercent =
    data && data.windows_total > 0 ? (data.windows_completed / data.windows_total) * 100 : initialLoading ? 5 : 0;

  if (error && !data && !initialLoading) {
    return (
      <main className="submission-loading-shell flex min-h-screen items-center justify-center px-6 py-12 text-[#f4eee0]">
        <div className="w-full max-w-2xl border border-[#b86048] bg-[#1b0d0b]/92 p-8 shadow-[0_24px_70px_rgba(0,0,0,0.42)] backdrop-blur-md">
          <p className="text-[12px] uppercase tracking-[0.32em] text-[#ffb39b]">Submission uplink failed</p>
          <h1 className="mt-4 text-[34px] uppercase tracking-[0.08em] text-[#fff0ea]">Unable to load the run state</h1>
          <p className="mt-4 text-[15px] leading-7 text-[#f8cec3]">{error}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                void refresh();
              }}
              className="border border-[#ffb39b] bg-[#ffb39b] px-5 py-3 text-[12px] uppercase tracking-[0.24em] text-[#1a0e0d]"
            >
              Retry
            </button>
            <button
              type="button"
              onClick={viewReport}
              className="border border-[#6d88a6] bg-transparent px-5 py-3 text-[12px] uppercase tracking-[0.24em] text-[#d5dfec]"
            >
              Open report
            </button>
          </div>
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
