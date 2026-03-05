"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";

import {
  apiJson,
  ArenaSubmissionOut,
  LeaderboardEntryOut,
  ModelPublicOut,
  ScenarioSetOut,
} from "@/app/lib/v4t";
import { NewRunFooter } from "@/app/components/NewRunFooter";
import { NewRunModal } from "@/app/components/NewRunModal";
import { MyRunsModal } from "@/app/components/MyRunsModal";
import { useRealtimeRefresh } from "@/app/lib/realtime";

function fmt(dt: string) {
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return dt;
  }
}

function pct(v: number) {
  if (Number.isNaN(v)) return "\u2013";
  const s = v >= 0 ? `+${v.toFixed(2)}` : v.toFixed(2);
  return `${s}%`;
}

function pctColor(v: number) {
  if (Number.isNaN(v)) return "text-zinc-400";
  return v >= 0
    ? "text-[color:var(--accent)] drop-shadow-[0_0_6px_var(--accent-glow)] font-bold"
    : "text-rose-400 drop-shadow-[0_0_6px_rgba(244,63,94,0.15)] font-bold";
}

export default function ArenaPage() {
  const showDemoControls = process.env.NODE_ENV !== "production";
  const router = useRouter();

  const [scenarioSets, setScenarioSets] = React.useState<ScenarioSetOut[]>([]);
  const [entries, setEntries] = React.useState<LeaderboardEntryOut[]>([]);
  const [scenarioSetKey, setScenarioSetKey] = React.useState<string>("");
  const [marketIdFilter, setMarketIdFilter] = React.useState<string>("");

  const [markets, setMarkets] = React.useState<string[]>([]);
  const [subs, setSubs] = React.useState<ArenaSubmissionOut[]>([]);
  const [models, setModels] = React.useState<ModelPublicOut[]>([]);
  const [marketsLoaded, setMarketsLoaded] = React.useState(false);
  const [modelsLoaded, setModelsLoaded] = React.useState(false);

  const [refreshing, setRefreshing] = React.useState(false);
  const [refreshError, setRefreshError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);
  const [createError, setCreateError] = React.useState<string | null>(null);

  const [startOpen, setStartOpen] = React.useState(false);
  const [myRunsOpen, setMyRunsOpen] = React.useState(false);

  const [marketId, setMarketId] = React.useState("");
  const [modelKey, setModelKey] = React.useState("stub");
  const [promptText, setPromptText] = React.useState("");

  React.useEffect(() => {
    apiJson<ModelPublicOut[]>("/models")
      .then((rows) => {
        setModels(rows);
        setModelKey((prev) => {
          if (rows.some((m) => m.model_key === prev)) return prev;
          return rows[0]?.model_key ?? "stub";
        });
      })
      .catch((e) => {
        setRefreshError(`Failed to load models: ${e instanceof Error ? e.message : String(e)}`);
        setModels([{ model_key: "stub", label: "Stub" }]);
        setModelKey("stub");
      })
      .finally(() => {
        setModelsLoaded(true);
      });
  }, []);

  const arenaConfigured = markets.length > 0;

  const refresh = React.useCallback(async () => {
    setRefreshing(true);
    setRefreshError(null);
    try {
      const params = new URLSearchParams();
      if (scenarioSetKey) params.set("scenario_set_key", scenarioSetKey);
      if (marketIdFilter) params.set("market_id", marketIdFilter);
      const qs = params.toString();

      const [marketsRes, subsRes, setsRes, lbRes] = await Promise.all([
        apiJson<string[]>("/arena/markets"),
        apiJson<ArenaSubmissionOut[]>("/arena/submissions"),
        apiJson<ScenarioSetOut[]>("/arena/scenario_sets"),
        apiJson<LeaderboardEntryOut[]>(
          `/arena/leaderboards${qs ? `?${qs}` : ""}`,
        ),
      ]);

      setMarkets(marketsRes);
      setSubs(subsRes);
      setScenarioSets(setsRes);
      setEntries(lbRes);

      setMarketId((prev) => {
        if (marketsRes.length === 0) return "";
        return marketsRes.includes(prev) ? prev : marketsRes[0];
      });

      if (!scenarioSetKey) {
        const preferred = setsRes.some((s) => s.key === "env-fullrange-v1")
          ? "env-fullrange-v1"
          : setsRes.some((s) => s.key === "env-regimes-v1")
            ? "env-regimes-v1"
            : setsRes.some((s) => s.key === "env-datasets-v1")
              ? "env-datasets-v1"
              : setsRes[0]?.key;
        if (preferred) setScenarioSetKey(preferred);
      }
    } catch (e) {
      setRefreshError(e instanceof Error ? e.message : String(e));
    } finally {
      setRefreshing(false);
      setMarketsLoaded(true);
    }
  }, [scenarioSetKey, marketIdFilter]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  useRealtimeRefresh({
    wsPath: "/runs/ws",
    enabled: !startOpen && !myRunsOpen,
    pollIntervalMs: 2500,
    refresh,
  });

  async function createSubmissionAndGo(input: {
    market_id: string;
    model_key: string;
    prompt_text: string;
  }) {
    if (submitting) return;
    setCreateError(null);

    if (!arenaConfigured) {
      setCreateError("Tournament datasets not configured on backend");
      return;
    }
    if (!input.market_id) {
      setCreateError("Select a coin");
      return;
    }
    if (!input.model_key) {
      setCreateError("Select a model");
      return;
    }
    if (!input.prompt_text.trim()) {
      setCreateError("Prompt text is required");
      return;
    }

    setSubmitting(true);
    try {
      const created = await apiJson<ArenaSubmissionOut>("/arena/submissions", {
        method: "POST",
        body: {
          market_id: input.market_id,
          model_key: input.model_key,
          prompt_text: input.prompt_text,
        },
      });

      setStartOpen(false);
      router.push(`/arena/submissions/${created.submission_id}`);
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function onStartNewRun() {
    await createSubmissionAndGo({
      market_id: marketId,
      model_key: modelKey,
      prompt_text: promptText,
    });
  }

  async function onSummonDemo() {
    if (!arenaConfigured) {
      setCreateError("Tournament datasets not configured on backend");
      return;
    }

    const demoModelKey =
      models.find((m) => m.model_key !== "stub")?.model_key ?? "stub";
    const demo = {
      market_id: markets[0] || "",
      model_key: demoModelKey,
      prompt_text:
        "E2E tournament prompt. Return a JSON object with schema_version=1, targets, confidence, rationale.",
    };

    setMarketId(demo.market_id);
    setModelKey(demo.model_key);
    setPromptText(demo.prompt_text);

    await createSubmissionAndGo(demo);
  }

  return (
    <div className="flex flex-col gap-8 pb-32 animate-rise">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold tracking-widest text-[color:var(--accent-2)]">
            COMPETITION
          </p>
          <h2 className="mt-2 font-display text-4xl tracking-tight text-white drop-shadow-sm">
            Tournament
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-zinc-400">
            All submissions ranked by compounded return across scenario windows.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {showDemoControls ? (
            <button
              type="button"
              onClick={onSummonDemo}
              className="rounded-full border border-[color:var(--accent-2)]/25 bg-[color:var(--accent-2)]/10 px-5 py-2.5 text-sm font-semibold text-[color:var(--accent-2)] transition-all hover:bg-[color:var(--accent-2)]/15 hover:border-[color:var(--accent-2)]/35 hover:shadow-[0_0_18px_var(--accent-2-glow)]"
              disabled={submitting || !arenaConfigured}
            >
              Summon Demo Run
            </button>
          ) : null}
          <button
            type="button"
            onClick={refresh}
            className="rounded-full border border-white/20 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-white/10 hover:border-white/30 hover:shadow-[0_0_15px_rgba(255,255,255,0.1)]"
          >
            {refreshing ? "Loading\u2026" : "Refresh"}
          </button>
        </div>
      </div>

      {refreshError ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm font-medium text-rose-200 shadow-[0_0_20px_rgba(244,63,94,0.1)] backdrop-blur-sm">
          {refreshError}
        </div>
      ) : null}

      {createError ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm font-medium text-rose-200 shadow-[0_0_20px_rgba(244,63,94,0.1)] backdrop-blur-sm">
          {createError}
        </div>
      ) : null}

      <section className="animate-rise-1 rounded-3xl border border-[color:var(--border)] bg-white/5 p-6 shadow-lg backdrop-blur-md">
        <h3 className="font-display text-xl tracking-tight text-white mb-6">Filters</h3>
        <div className="grid gap-5 md:grid-cols-2">
          <label className="grid gap-1.5 text-sm">
            <span className="text-zinc-400 font-medium">scenario_set_key</span>
            <div className="relative">
              <select
                value={scenarioSetKey}
                onChange={(e) => setScenarioSetKey(e.target.value)}
                className="w-full h-11 appearance-none rounded-xl border border-white/10 bg-black/40 px-4 font-mono text-xs text-white focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all"
              >
                <option value="">(all)</option>
                {scenarioSets.map((s) => (
                  <option key={s.key} value={s.key}>
                    {s.name} &mdash; {s.key}
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-zinc-500">
                <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
                  <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                </svg>
              </div>
            </div>
          </label>

          <label className="grid gap-1.5 text-sm">
            <span className="text-zinc-400 font-medium">market_id</span>
            <input
              value={marketIdFilter}
              onChange={(e) => setMarketIdFilter(e.target.value)}
              placeholder="(all)"
              className="h-11 rounded-xl border border-white/10 bg-black/40 px-4 font-mono text-xs text-white placeholder-zinc-600 focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all"
            />
          </label>
        </div>
      </section>

      <section className="animate-rise-2 overflow-hidden rounded-3xl border border-[color:var(--border)] bg-white/5 shadow-lg backdrop-blur-md">
        <div className="flex items-center justify-between border-b border-white/10 bg-white/5 px-6 py-5">
          <h3 className="font-display text-xl tracking-tight text-white flex items-center gap-2">
            <svg
              className="w-5 h-5 text-[color:var(--accent-2)]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            Rankings
          </h3>
          <div className="rounded-full bg-white/10 px-3 py-1.5 text-xs font-medium text-white shadow-inner">
            {entries.length} entries
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-black/20 text-xs uppercase tracking-wider text-zinc-400">
              <tr>
                <th className="px-6 py-4 font-semibold">Rank</th>
                <th className="px-6 py-4 font-semibold">Submission</th>
                <th className="px-6 py-4 font-semibold">Total</th>
                <th className="px-6 py-4 font-semibold">Avg</th>
                <th className="px-6 py-4 font-semibold">Market</th>
                <th className="px-6 py-4 font-semibold">Model</th>
                <th className="px-6 py-4 font-semibold">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {entries.map((e, idx) => (
                <tr key={e.submission_id} className="transition-colors hover:bg-white/5">
                  <td className="px-6 py-4 font-mono text-xs text-white font-bold">{idx + 1}</td>
                  <td className="px-6 py-4">
                    <Link
                      href={`/arena/submissions/${e.submission_id}`}
                      className="font-mono text-xs text-[color:var(--accent)] hover:text-white transition-colors"
                    >
                      {e.submission_id.slice(0, 8)}&hellip;
                    </Link>
                    <div className="mt-1.5 text-xs font-medium text-zinc-500">
                      {e.scenario_set_key}
                    </div>
                  </td>
                  <td className={`px-6 py-4 font-mono text-xs ${pctColor(e.total_return_pct)}`}>
                    {pct(e.total_return_pct)}
                  </td>
                  <td className={`px-6 py-4 font-mono text-xs ${pctColor(e.avg_return_pct)}`}>
                    {pct(e.avg_return_pct)}
                  </td>
                  <td className="px-6 py-4 font-mono text-xs text-zinc-300">{e.market_id}</td>
                  <td className="px-6 py-4">
                    <span className="font-mono text-xs text-[color:var(--accent-2)]">
                      {e.model_key}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-mono text-xs text-zinc-400">{fmt(e.created_at)}</td>
                </tr>
              ))}
              {entries.length === 0 ? (
                <tr>
                  <td className="px-6 py-12 text-center text-sm text-zinc-500" colSpan={7}>
                    <div className="flex flex-col items-center justify-center space-y-3">
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
                          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                        />
                      </svg>
                      <p>No finished submissions yet.</p>
                    </div>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <NewRunFooter
        onMyRuns={() => setMyRunsOpen(true)}
        onNewRun={() => {
          setCreateError(null);
          setStartOpen(true);
        }}
        disabled={!arenaConfigured || submitting}
      />

      <MyRunsModal
        open={myRunsOpen}
        submissions={subs}
        onClose={() => setMyRunsOpen(false)}
      />
      <NewRunModal
        open={startOpen}
        markets={markets}
        models={models}
        marketsLoaded={marketsLoaded}
        modelsLoaded={modelsLoaded}
        marketId={marketId}
        modelKey={modelKey}
        promptText={promptText}
        onChangeMarketId={(v) => {
          setMarketId(v);
          setCreateError(null);
        }}
        onChangeModelKey={(v) => {
          setModelKey(v);
          setCreateError(null);
        }}
        onChangePromptText={(v) => {
          setPromptText(v);
          setCreateError(null);
        }}
        onClose={() => {
          setStartOpen(false);
          setCreateError(null);
        }}
        onSubmit={onStartNewRun}
        submitting={submitting}
        submitError={createError}
      />
    </div>
  );
}
