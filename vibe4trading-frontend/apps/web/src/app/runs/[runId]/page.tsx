"use client";

import * as React from "react";

import Link from "next/link";
import { useParams } from "next/navigation";

import { useRealtimeRefresh } from "@/app/lib/realtime";
import { apiJson, LlmDecision, RunOut, SummaryOut, TimelinePoint } from "@/app/lib/v4t";

import { CircularLoading } from "@/app/components/CircularLoading";
import { EventModal } from "@/app/components/EventModal";
import { ReportHero } from "@/app/components/ReportHero";
import { ReportMetrics } from "@/app/components/ReportMetrics";
import { ReportViz } from "@/app/components/ReportViz";
import { ReportHeatmap } from "@/app/components/ReportHeatmap";
import { storyCards } from "@/app/lib/report-data";

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

function runBadge(status: string) {
  if (status === "finished") return "bg-[color:var(--accent)]/10 text-[color:var(--accent)] border border-[color:var(--accent)]/30 drop-shadow-[0_0_8px_var(--accent-glow)]";
  if (status === "running") return "bg-[color:var(--accent-2)]/10 text-[color:var(--accent-2)] border border-[color:var(--accent-2)]/30 drop-shadow-[0_0_8px_var(--accent-2-glow)]";
  if (status === "failed") return "bg-rose-500/10 text-rose-400 border border-rose-500/30";
  return "bg-zinc-500/10 text-zinc-400 border border-zinc-500/30";
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
  const olderOffsetRef = React.useRef(olderOffset);
  olderOffsetRef.current = olderOffset;
  const [hasMoreDecisions, setHasMoreDecisions] = React.useState(true);
  const [loadingMore, setLoadingMore] = React.useState(false);

  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Retro Report Modal State
  const [activeEvent, setActiveEvent] = React.useState<string | null>(null);
  const [highlightedEvent, setHighlightedEvent] = React.useState<string | null>(null);
  const [modalOpen, setModalOpen] = React.useState(false);
  const [selectedEvent, setSelectedEvent] = React.useState<string | null>(null);

  const handleEventClick = (eventCode: string) => {
    setSelectedEvent(eventCode);
    setActiveEvent(eventCode);
    setModalOpen(true);
  };

  const handleEventHover = (eventCode: string | null) => {
    setHighlightedEvent(eventCode);
  };

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
      if (olderOffsetRef.current === 0) {
        setHasMoreDecisions(decRes.length === PAGE_SIZE);
      }
      setSummary(summaryRes.summary_text);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [runId]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const status = run?.status;
  const shouldRefresh = !status || status === "pending" || status === "running";
  useRealtimeRefresh({
    wsPath: shouldRefresh ? `/runs/${runId}/ws` : null,
    enabled: shouldRefresh,
    pollIntervalMs: 2500,
    refresh,
  });

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

  const isRunning = run?.status === "running" || run?.status === "pending" || run?.status === "submitted" || !run;

  if (isRunning) {
    return <CircularLoading status={run?.status || "pending"} />;
  }

  return (
    <div className="canvas animate-rise" style={{ margin: "-40px -20px" }}>
      <main className="layout">
        <section className="left-column">
          <ReportHero run={run} summary={summary} />
          <ReportMetrics />
          <ReportViz
            run={run}
            highlightedEvent={highlightedEvent}
            onEventHover={handleEventHover}
            onEventClick={handleEventClick}
          />
          <footer className="leaderboard block">
            <span>GLOBAL RANK</span>
            <strong>#37</strong>
            <em>你超过了 12,482 名用户</em>
          </footer>
        </section>

        <ReportHeatmap
          activeEvent={activeEvent}
          highlightedEvent={highlightedEvent}
          onEventHover={handleEventHover}
          onEventClick={handleEventClick}
        />
      </main>

      <EventModal
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setActiveEvent(null);
        }}
        eventData={selectedEvent ? storyCards[selectedEvent] : null}
        eventCode={selectedEvent || ""}
      />
    </div>
  );
}
