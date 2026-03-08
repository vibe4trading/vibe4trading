import { Link } from "react-router-dom";
import * as React from "react";

import { useNewRunModal } from "@/app/components/NewRunProvider";
import { useRealtimeRefresh } from "@/app/lib/realtime";
import { getSubmissionStatusDisplay } from "@/app/lib/submissionStatus";
import { apiJson, ArenaSubmissionIndexOut, ArenaSubmissionOut } from "@/app/lib/v4t";

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
  const [subs, setSubs] = React.useState<ArenaSubmissionOut[]>([]);
  const [subsCursor, setSubsCursor] = React.useState<string | null>(null);
  const [subsHasMore, setSubsHasMore] = React.useState(false);
  const [refreshError, setRefreshError] = React.useState<string | null>(null);
  const [loadingMore, setLoadingMore] = React.useState(false);

  const refreshSubmissions = React.useCallback(() => {
    setRefreshError(null);
    apiJson<ArenaSubmissionIndexOut>("/arena/submissions")
      .then((res) => {
        setSubs((current) => mergeSubmissions(current, res.items));
        setSubsCursor(res.next_cursor);
        setSubsHasMore(res.has_more);
      })
      .catch((e) => setRefreshError(e instanceof Error ? e.message : String(e)));
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

  const hasActiveSubmissions = React.useMemo(
    () => subs.some((row) => row.status === "pending" || row.status === "running"),
    [subs],
  );

  useRealtimeRefresh({
    wsPath: hasActiveSubmissions ? "/runs/ws" : null,
    enabled: hasActiveSubmissions,
    pollIntervalMs: 2500,
    refresh: refreshSubmissions,
  });

  return (
    <main className="trials-page-main animate-rise">
      <section className="trials-head block">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h1>TRIALS / Historical Prompt Records</h1>
            <p>Open any submission to inspect the full report across the scenario set.</p>
          </div>
          <button type="button" className="newrun-action-btn" onClick={openNewRun}>
            Start a new run
          </button>
        </div>
        {refreshError && <p className="text-red-600 mt-2">{refreshError}</p>}
      </section>

      <section className="trials-list block">
        {subs.length === 0 && !refreshError && (
          <div className="p-4 text-center text-[#555]">No recent runs found.</div>
        )}
        {subs.map((row) => (
          (() => {
            const statusDisplay = getSubmissionStatusDisplay({
              status: row.status,
              startedAt: row.started_at,
            });

            return (
              <Link
                key={row.submission_id}
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
            );
          })()
        ))}
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
