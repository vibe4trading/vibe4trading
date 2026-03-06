"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";

import { useNewRunModal } from "@/app/components/NewRunProvider";
import { saveSubmissionLoadingSnapshot } from "@/app/lib/submissionLoading";
import { apiJson, ArenaSubmissionIndexOut, ArenaSubmissionOut, ModelPublicOut } from "@/app/lib/v4t";

function firstSelectableModelKey(rows: ModelPublicOut[]) {
  return rows.find((row) => row.selectable)?.model_key ?? "";
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
  const router = useRouter();
  const { openNewRun } = useNewRunModal();
  const [subs, setSubs] = React.useState<ArenaSubmissionOut[]>([]);
  const [subsCursor, setSubsCursor] = React.useState<string | null>(null);
  const [subsHasMore, setSubsHasMore] = React.useState(false);
  const [refreshError, setRefreshError] = React.useState<string | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [markets, setMarkets] = React.useState<string[]>([]);
  const [models, setModels] = React.useState<ModelPublicOut[]>([]);
  const [marketId, setMarketId] = React.useState("");
  const [modelKey, setModelKey] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [loadingMore, setLoadingMore] = React.useState(false);

  const refreshSubmissions = React.useCallback(() => {
    apiJson<ArenaSubmissionIndexOut>("/arena/submissions")
      .then((res) => {
        setSubs(res.items);
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

  React.useEffect(() => {
    apiJson<string[]>("/arena/markets")
      .then((res) => {
        setMarkets(res);
        setMarketId((current) => current || res[0] || "");
      })
      .catch((e) => setActionError(e instanceof Error ? e.message : String(e)));

    apiJson<ModelPublicOut[]>("/models")
      .then((res) => {
        setModels(res);
        setModelKey((current) => {
          if (res.some((row) => row.model_key === current && row.selectable)) return current;
          return firstSelectableModelKey(res);
        });
      })
      .catch((e) => setActionError(e instanceof Error ? e.message : String(e)));
  }, []);

  async function startRun(promptText: string) {
    setSubmitting(true);
    setActionError(null);
    try {
      const body = await apiJson<{ submission_id: string }>("/arena/submissions", {
        method: "POST",
        body: {
          market_id: marketId,
          model_key: modelKey,
          prompt_text: promptText,
          visibility: "public",
        },
      });
      saveSubmissionLoadingSnapshot(body.submission_id, {
        marketId,
        modelKey,
        promptText,
      });
      router.push(`/arena/submissions/${body.submission_id}/loading`);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function summonDemoRun() {
    if (!marketId || !modelKey) {
      setActionError("Arena configuration is still loading.");
      return;
    }
    await startRun(
      'You are a crypto trading agent. Return ONLY JSON like {"schema_version":1,"targets":{"<market_id>":0.25},"next_check_seconds":600,"confidence":0.6,"key_signals":["demo"],"rationale":"demo run"}',
    );
  }

  return (
    <main className="trials-page-main animate-rise">
      <section className="trials-head block">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h1>TRIALS / Historical Prompt Records</h1>
            <p>Open any submission to inspect the full report across the scenario set.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="newrun-action-btn ghost" onClick={openNewRun}>
              Start a new run
            </button>
            <button
              type="button"
              className="newrun-action-btn"
              onClick={summonDemoRun}
              disabled={submitting || markets.length === 0 || !models.some((row) => row.selectable)}
            >
              {submitting ? "Starting..." : "Summon Demo Run"}
            </button>
          </div>
        </div>
        {refreshError && <p className="text-red-600 mt-2">{refreshError}</p>}
        {actionError && <p className="text-red-600 mt-2">{actionError}</p>}
      </section>

      <section className="trials-list block">
        {subs.length === 0 && !refreshError && (
          <div className="p-4 text-center text-[#555]">No recent runs found.</div>
        )}
        {subs.map((row) => (
          <Link
            key={row.submission_id}
            href={`/arena/submissions/${row.submission_id}`}
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
                {row.status && <span>Status: {row.status}</span>}
                {row.windows_total > 0 && (
                  <span>
                    Progress: {row.windows_completed}/{row.windows_total}
                  </span>
                )}
              </div>
            </div>
          </Link>
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
