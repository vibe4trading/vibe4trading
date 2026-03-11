import { Link } from "react-router-dom";
import * as React from "react";

import { Helmet } from "react-helmet-async";
import { SEO } from "@/app/components/SEO";
import { useAuth } from "@/auth";
import { useNewRunModal } from "@/app/components/NewRunProvider";
import { useRealtimeRefresh } from "@/app/lib/realtime";
import { getSubmissionStatusDisplay } from "@/app/lib/submissionStatus";
import { apiJson, ArenaSubmissionIndexOut, ArenaSubmissionOut } from "@/app/lib/v4t";
import { usePrerenderReady } from "@/app/hooks/usePrerenderReady";
import { useProductTour } from "@/app/hooks/useProductTour";
import { useTourPersistence } from "@/app/hooks/useTourPersistence";
import { useTourContext } from "@/app/components/TourProvider";
import { trialsSteps } from "@/app/tours/trials-tour";

function mergeSubmissions(current: ArenaSubmissionOut[], fresh: ArenaSubmissionOut[]) {
  const freshIds = new Set(fresh.map((submission) => submission.submission_id));
  return [...fresh, ...current.filter((submission) => !freshIds.has(submission.submission_id))];
}

function fmt(dt: string) {
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return dt;
  }
}

function pairName(marketId: string) {
  const parts = marketId.split(":");
  return parts[parts.length - 1] ?? marketId;
}

export default function ArenaPage() {
  const { openNewRun } = useNewRunModal();
  const { user } = useAuth();
  const isAdmin = Boolean(user?.is_admin);
  const [subs, setSubs] = React.useState<ArenaSubmissionOut[]>([]);
  const [subsCursor, setSubsCursor] = React.useState<string | null>(null);
  const [subsHasMore, setSubsHasMore] = React.useState(false);
  const [refreshError, setRefreshError] = React.useState<string | null>(null);
  const [loadingMore, setLoadingMore] = React.useState(false);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [initialLoadDone, setInitialLoadDone] = React.useState(false);

  const trialsPersistence = useTourPersistence("trials-v1");
  const trialsTour = useProductTour(trialsSteps);
  const { activeTour, stopTour } = useTourContext();

  React.useEffect(() => {
    if (!trialsPersistence.hasCompleted()) {
      const timeoutId = window.setTimeout(() => {
        trialsTour.start();
        trialsPersistence.markCompleted();
      }, 500);
      return () => window.clearTimeout(timeoutId);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  React.useEffect(() => {
    if (activeTour === "trials-v1") {
      trialsTour.start();
      stopTour();
    }
  }, [activeTour]); // eslint-disable-line react-hooks/exhaustive-deps

  const refreshSubmissions = React.useCallback(() => {
    setRefreshError(null);
    apiJson<ArenaSubmissionIndexOut>("/arena/submissions")
      .then((res) => {
        setSubs((current) => mergeSubmissions(current, res.items));
        setSubsCursor(res.next_cursor);
        setSubsHasMore(res.has_more);
      })
      .catch((e) => setRefreshError(e instanceof Error ? e.message : String(e)))
      .finally(() => setInitialLoadDone(true));
  }, []);

  async function loadMoreSubmissions() {
    if (!subsCursor) return;
    setLoadingMore(true);
    setRefreshError(null);
    try {
      const res = await apiJson<ArenaSubmissionIndexOut>(
        `/arena/submissions?cursor=${encodeURIComponent(subsCursor)}`,
      );
      setSubs((current) => [...current, ...res.items]);
      setSubsCursor(res.next_cursor);
      setSubsHasMore(res.has_more);
    } catch (e) {
      setRefreshError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingMore(false);
    }
  }

  React.useEffect(() => {
    refreshSubmissions();
  }, [refreshSubmissions]);

  async function handleDeleteSubmission(submissionId: string) {
    const confirmed = window.confirm(
      "Permanently delete this trial and all its runs, events, and LLM calls? This cannot be undone.",
    );
    if (!confirmed) return;

    setDeletingId(submissionId);
    setRefreshError(null);
    try {
      await apiJson<{ deleted: boolean }>(
        `/admin/arena/submissions/${submissionId}`,
        { method: "DELETE" },
      );
      setSubs((current) => current.filter((s) => s.submission_id !== submissionId));
    } catch (e) {
      setRefreshError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeletingId(null);
    }
  }

  const hasActiveSubmissions = React.useMemo(
    () => subs.some((row) => row.status === "pending" || row.status === "running"),
    [subs],
  );

  usePrerenderReady(initialLoadDone);

  useRealtimeRefresh({
    wsPath: hasActiveSubmissions ? "/runs/ws" : null,
    enabled: hasActiveSubmissions,
    pollIntervalMs: 2500,
    refresh: refreshSubmissions,
  });

  return (
    <main className="trials-page-main animate-rise">
      <SEO
        title="Strategy Arena — Web4 AI Trading Agent Benchmarks"
        description="Submit your AI trading agent to the Web4 arena. Benchmark across 10 real crypto market scenarios. Scored on returns, Sharpe ratio, drawdown, and more. Web3 + AI."
        canonicalPath="/arena"
      />
      <Helmet>
        <script type="application/ld+json">{JSON.stringify({
          "@context": "https://schema.org",
          "@type": "WebApplication",
          "name": "Vibe4Trading Strategy Arena",
          "url": "https://vibe4trading.ai/arena",
          "applicationCategory": "FinanceApplication",
          "operatingSystem": "Web",
          "description": "Submit your AI trading agent to the arena. Benchmark across 10 real crypto market scenarios scored on returns, Sharpe ratio, drawdown, and more.",
          "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD"
          }
        })}</script>
      </Helmet>
      <section className="trials-head block">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h1>TRIALS / Historical Prompt Records</h1>
            <p>Open any submission to inspect the full report across the scenario set.</p>
          </div>
          <button type="button" className="newrun-action-btn" data-tour="trials-new-run-button" onClick={openNewRun}>
            Start a new run
          </button>
        </div>
        {refreshError && <p className="text-red-600 mt-2">{refreshError}</p>}
      </section>

      <section className="trials-list block" data-tour="trials-submissions-list">
        {subs.length === 0 && !refreshError && (
          <div className="p-4 text-center text-[#555]">No recent runs found.</div>
        )}
        {subs.map((row) =>
          (() => {
            const statusDisplay = getSubmissionStatusDisplay({
              status: row.status,
              startedAt: row.started_at,
            });

            return (
              <div key={row.submission_id} className="relative">
                <Link
                  to={`/arena/submissions/${row.submission_id}`}
                  className="trial-row"
                >
                  <div className="trial-meta">
                    <strong>{row.submission_id.slice(0, 8)}</strong>
                    <span>{fmt(row.created_at)}</span>
                  </div>
                  <div className="trial-main">
                    <p className="trial-prompt">Scenario: {row.scenario_set_key}</p>
                    <div className="trial-tags">
                      <span>Model: {row.model_key}</span>
                      <span>Pair: {pairName(row.market_id)}</span>
                      {row.status && <span>Status: {statusDisplay.label}</span>}
                      {statusDisplay.isQueued ? <span>Waiting for worker</span> : null}
                      {row.windows_total > 0 && (
                        <span>
                          Progress: {row.windows_completed}/{row.windows_total}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
                {isAdmin && (
                  <button
                    type="button"
                    className="absolute top-2 right-2 border-2 px-2 py-1 text-sm"
                    style={{
                      color: "var(--red)",
                      borderColor: "var(--red)",
                      background: "var(--panel)",
                      cursor: "pointer",
                    }}
                    disabled={deletingId === row.submission_id}
                    onClick={() => handleDeleteSubmission(row.submission_id)}
                  >
                    {deletingId === row.submission_id ? "Deleting\u2026" : "Delete"}
                  </button>
                )}
              </div>
            );
          })(),
        )}
        {subsHasMore ? (
          <div className="flex justify-center pt-4">
            <button
              type="button"
              className="newrun-action-btn ghost"
              onClick={loadMoreSubmissions}
              disabled={loadingMore}
            >
              {loadingMore ? "Loading..." : "Load more"}
            </button>
          </div>
        ) : null}
      </section>
    </main>
  );
}
