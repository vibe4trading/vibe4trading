import { Link } from "react-router-dom";
import * as React from "react";

import { Helmet } from "react-helmet-async";
import { SEO } from "@/app/components/SEO";
import {
    apiJson,
    LeaderboardEntryOut,
    ModelPublicOut,
    ScenarioSetOut,
} from "@/app/lib/v4t";
import { useProductTour } from "@/app/hooks/useProductTour";
import { usePrerenderReady } from "@/app/hooks/usePrerenderReady";
import { useTourPersistence } from "@/app/hooks/useTourPersistence";
import { useTourContext } from "@/app/components/TourProvider";
import { leaderboardSteps } from "@/app/tours/leaderboard-tour";
import { useTranslation } from "react-i18next";

function pct(v: number | null | undefined) {
    if (v == null || Number.isNaN(v)) return "\u2013";
    const s = v >= 0 ? `+${v.toFixed(2)}` : v.toFixed(2);
    return `${s}%`;
}

function pctClass(v: number | null | undefined) {
    if (v == null || Number.isNaN(v)) return "";
    return v >= 0 ? "lb-value-pos" : "lb-value-neg";
}

function pairName(marketId: string) {
    const parts = marketId.split(":");
    return parts[parts.length - 1];
}

function stat(v: number | null | undefined, decimals = 2) {
    if (v == null || Number.isNaN(v)) return "\u2013";
    return v.toFixed(decimals);
}

export default function LeaderboardPage() {
    const { t } = useTranslation("arena");
    const [entries, setEntries] = React.useState<LeaderboardEntryOut[]>([]);
    const [models, setModels] = React.useState<ModelPublicOut[]>([]);
    const [markets, setMarkets] = React.useState<string[]>([]);
    const [initialEquity, setInitialEquity] = React.useState<number | null>(null);

    const [modelFilter, setModelFilter] = React.useState<string>("ALL");
    const [marketFilter, setMarketFilter] = React.useState<string>("ALL");

    const [refreshing, setRefreshing] = React.useState(false);
    const [refreshError, setRefreshError] = React.useState<string | null>(null);
    const [filterLoadError, setFilterLoadError] = React.useState<string | null>(null);
    const [selectedId, setSelectedId] = React.useState<string | null>(null);
    const [initialLoadDone, setInitialLoadDone] = React.useState(false);

    const leaderboardPersistence = useTourPersistence("leaderboard-v1");
    const leaderboardTour = useProductTour(leaderboardSteps);
    const { activeTour, stopTour } = useTourContext();

    React.useEffect(() => {
        if (!leaderboardPersistence.hasCompleted()) {
            const timeoutId = window.setTimeout(() => {
                leaderboardTour.start();
                leaderboardPersistence.markCompleted();
            }, 500);
            return () => window.clearTimeout(timeoutId);
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    React.useEffect(() => {
        if (activeTour === "leaderboard-v1") {
            leaderboardTour.start();
            stopTour();
        }
    }, [activeTour]); // eslint-disable-line react-hooks/exhaustive-deps

    React.useEffect(() => {
        let cancelled = false;

        void Promise.allSettled([
            apiJson<ModelPublicOut[]>("/models"),
            apiJson<string[]>("/arena/markets"),
            apiJson<ScenarioSetOut[]>("/arena/scenario_sets"),
        ]).then((results) => {
            if (cancelled) return;

            const [modelsResult, marketsResult, scenarioResult] = results;
            const errors: string[] = [];

            if (modelsResult.status === "fulfilled") {
                setModels(modelsResult.value);
            } else {
                errors.push(modelsResult.reason instanceof Error ? modelsResult.reason.message : String(modelsResult.reason));
            }

            if (marketsResult.status === "fulfilled") {
                setMarkets(marketsResult.value);
            } else {
                errors.push(marketsResult.reason instanceof Error ? marketsResult.reason.message : String(marketsResult.reason));
            }

            if (scenarioResult.status === "fulfilled" && scenarioResult.value.length > 0) {
                setInitialEquity(scenarioResult.value[0].initial_equity_quote);
            }

            setFilterLoadError(errors.length > 0 ? errors.join(" ") : null);
        });

        return () => {
            cancelled = true;
        };
    }, []);

    const refresh = React.useCallback(async () => {
        setRefreshing(true);
        setRefreshError(null);
        try {
            const params = new URLSearchParams();
            if (modelFilter !== "ALL") params.set("model_key", modelFilter);
            if (marketFilter !== "ALL") params.set("market_id", marketFilter);
            const qs = params.toString();

            const lbRes = await apiJson<LeaderboardEntryOut[]>(
                `/arena/leaderboards${qs ? `?${qs}` : ""}`,
            );

            setEntries(lbRes);
            setSelectedId((current) => {
                if (current && lbRes.some((entry) => entry.submission_id === current)) {
                    return current;
                }
                return lbRes[0]?.submission_id ?? null;
            });
        } catch (e) {
            setRefreshError(e instanceof Error ? e.message : String(e));
        } finally {
            setRefreshing(false);
            setInitialLoadDone(true);
        }
    }, [modelFilter, marketFilter]);

    React.useEffect(() => {
        const timer = setTimeout(() => { refresh(); }, 300);
        return () => clearTimeout(timer);
    }, [refresh]);

    usePrerenderReady(initialLoadDone);

    const selected = entries.find((e) => e.submission_id === selectedId) ?? null;
    const selectedRank = selected ? entries.indexOf(selected) + 1 : 0;

    const topPnl = entries.length > 0 ? entries[0] : null;

    return (
        <main className="leaderboard-page-main animate-rise">
            <SEO
                title={t("meta.leaderboard.title")}
                description={t("meta.leaderboard.description")}
                canonicalPath="/leaderboard"
            />
            <Helmet>
                <script type="application/ld+json">{JSON.stringify({
                    "@context": "https://schema.org",
                    "@type": "Dataset",
                    "name": "Vibe4Trading AI Trading Agent Leaderboard",
                    "url": "https://vibe4trading.ai/leaderboard",
                    "description": "Ranked leaderboard of autonomous AI trading agents benchmarked across real crypto market scenarios. Scored by total return, Sharpe ratio, max drawdown, win rate, and profit factor.",
                    "creator": {
                        "@type": "Organization",
                        "name": "Vibe4Trading"
                    },
                    "variableMeasured": [
                        "Total Return",
                        "Sharpe Ratio",
                        "Max Drawdown",
                        "Win Rate",
                        "Profit Factor",
                        "Trade Count"
                    ]
                })}</script>
            </Helmet>
            {/* PAGE HEADER */}
            <section className="leaderboard-screen-head block">
                <div className="lb-title-line">
                    <h1>{t("leaderboard.title")}</h1>
                    <div className="lb-live-status">
                        <i className="live-dot" />
                        <strong>{t("leaderboard.historicalRanking")}</strong>
                        <em>--:--</em>
                    </div>
                </div>
                <p>
                    {t("leaderboard.description")}
                </p>

                <div className="lb-filter-grid" data-tour="leaderboard-filters">
                    <label>
                        {t("leaderboard.model")}
                        <select
                            value={modelFilter}
                            onChange={(e) => setModelFilter(e.target.value)}
                        >
                            <option value="ALL">{t("leaderboard.allModels")}</option>
                            {models.map((m) => (
                                <option key={m.model_key} value={m.model_key}>
                                    {m.label ? `${m.label} (${m.model_key})` : m.model_key}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label>
                        {t("leaderboard.pair")}
                        <select
                            value={marketFilter}
                            onChange={(e) => setMarketFilter(e.target.value)}
                        >
                            <option value="ALL">{t("leaderboard.allPairs")}</option>
                            {markets.map((m) => (
                                <option key={m} value={m}>
                                    {pairName(m)}
                                </option>
                            ))}
                        </select>
                    </label>
                </div>
            </section>

            {(filterLoadError || refreshError) && (
                <div className="bg-[#f9e5e5] border-2 border-[#c0392b] text-[#c0392b] p-3 text-lg mb-4">
                    {[filterLoadError, refreshError].filter(Boolean).join(" ")}
                </div>
            )}

            {/* KPI CARDS */}
            <section className="lb-kpi-grid" data-tour="leaderboard-kpi-cards">
                <article className="lb-kpi-card">
                    <span>{t("leaderboard.filteredResults")}</span>
                    <strong>{entries.length}</strong>
                    <em>{t("leaderboard.currentFilter")}</em>
                </article>
                <article className="lb-kpi-card">
                    <span>{t("leaderboard.topPnl")}</span>
                    <strong className={pctClass(topPnl?.total_return_pct)}>
                        {topPnl ? pct(topPnl.total_return_pct) : "\u2013"}
                    </strong>
                    <em>{topPnl?.model_key ?? "\u2013"}</em>
                </article>
                <article className="lb-kpi-card">
                    <span>{t("leaderboard.topSharpe")}</span>
                    <strong>{topPnl ? stat(topPnl.sharpe_ratio) : "\u2013"}</strong>
                    <em>{t("leaderboard.riskAdjusted")}</em>
                </article>
                <article className="lb-kpi-card">
                    <span>{t("leaderboard.topMaxDD")}</span>
                    <strong>{topPnl ? `${stat(topPnl.max_drawdown_pct)}%` : "\u2013"}</strong>
                    <em>{t("leaderboard.worstPeakToTrough")}</em>
                </article>
            </section>

            {/* TABLE + SIDE PANEL */}
            <section className="lb-main-grid">
                {/* LEFT: TABLE */}
                <section className="leaderboard-proto block">
                    <header className="lb-head">
                        <div>
                            <h2>{t("leaderboard.top100")}</h2>
                            <p>{t("leaderboard.topModels")}</p>
                        </div>
                        <div className="lb-head-metrics">
                            <span>{t("leaderboard.startBalance")}: {initialEquity != null ? `${initialEquity.toLocaleString()} USDT` : "–"}</span>
                            <span>{t("leaderboard.entries")}: {entries.length}</span>
                            <span>{t("leaderboard.updated")}: {t("leaderboard.live")}</span>
                        </div>
                    </header>

                    <div className="lb-scroll-shell" data-tour="leaderboard-table">
                        <div className="lb-row lb-row-head">
                            <span>{t("leaderboard.rank")}</span>
                            <span>{t("leaderboard.model")}</span>
                            <span>{t("leaderboard.pair")}</span>
                            <span>{t("leaderboard.pnl")}</span>
                        </div>
                        <div className="lb-scroll">
                            {entries.map((e, idx) => {
                                const globalRank = idx + 1;
                                const pnlClass = pctClass(e.total_return_pct);
                                const rankClass = globalRank <= 3 ? `top-${globalRank}` : "";
                                const isSelected = e.submission_id === selectedId;
                                const rowClass = `lb-row ${e.total_return_pct >= 0 ? "up" : "down"} ${rankClass} ${isSelected ? "is-selected" : ""}`;

                                return (
                                    <div
                                        key={e.submission_id}
                                        className={rowClass}
                                        onClick={() => setSelectedId(e.submission_id)}
                                    >
                                        <span>#{String(globalRank).padStart(3, "0")}</span>
                                        <span>{e.model_key}</span>
                                        <span>{pairName(e.market_id)}</span>
                                        <span className={pnlClass}>{pct(e.total_return_pct)}</span>
                                    </div>
                                );
                            })}
                            {entries.length === 0 && !refreshing && (
                                <div className="text-center p-8 text-[#555]">{t("leaderboard.noEntries")}</div>
                            )}
                            {refreshing && (
                                <div className="text-center p-8 text-[#555]">{t("leaderboard.loading")}</div>
                            )}
                        </div>
                    </div>
                </section>

                {/* RIGHT: SIDE PANEL */}
                <aside className="lb-side-panel block" data-tour="leaderboard-side-panel">
                    {selected ? (
                        <>
                            <h3>{t("leaderboard.strategyDetails")}</h3>

                            <div className="lb-selected-meta">
                                <strong>
                                    #{String(selectedRank).padStart(3, "0")} · {selected.model_key}
                                </strong>
                                <p>{pairName(selected.market_id)}</p>
                                <p>{t("leaderboard.liveComparison")}</p>
                            </div>

                            {/* Stats grid 2x3 */}
                            <div className="lb-selected-stat-grid">
                                <div className="lb-selected-stat">
                                    <span>{t("leaderboard.totalPnl")}</span>
                                    <strong className={pctClass(selected.total_return_pct)}>
                                        {pct(selected.total_return_pct)}
                                    </strong>
                                </div>
                                <div className="lb-selected-stat">
                                    <span>{t("leaderboard.winRate")}</span>
                                    <strong>
                                        {selected.win_rate_pct != null
                                            ? `${stat(selected.win_rate_pct, 1)}%`
                                            : "\u2013"}
                                    </strong>
                                </div>
                                <div className="lb-selected-stat">
                                    <span>{t("leaderboard.sharpe")}</span>
                                    <strong>{stat(selected.sharpe_ratio)}</strong>
                                </div>
                                <div className="lb-selected-stat">
                                    <span>{t("leaderboard.profitFactor")}</span>
                                    <strong>{stat(selected.profit_factor)}</strong>
                                </div>
                                <div className="lb-selected-stat">
                                    <span>{t("leaderboard.maxDD")}</span>
                                    <strong>
                                        {selected.max_drawdown_pct != null
                                            ? `${stat(selected.max_drawdown_pct, 1)}%`
                                            : "\u2013"}
                                    </strong>
                                </div>
                                <div className="lb-selected-stat">
                                    <span>{t("leaderboard.trades")}</span>
                                    <strong>
                                        {selected.num_trades != null ? String(selected.num_trades) : "\u2013"}
                                    </strong>
                                </div>
                            </div>

                            {/* Event performance tiles */}
                            {selected.per_window_returns && selected.per_window_returns.length > 0 && (
                                <div className="lb-event-grid">
                                    {selected.per_window_returns.map((v, i) => {
                                        const isUp = v >= 0;
                                        const fillH = `${Math.min(100, Math.abs(v) * 8)}%`;
                                        return (
                                            <div
                                                key={i}
                                                className={`lb-event-tile ${isUp ? "up" : "down"}`}
                                            >
                                                <div className="lb-event-label">
                                                    <span>W{String(i + 1).padStart(2, "0")}</span>
                                                    <span>
                                                        {v >= 0 ? "+" : ""}
                                                        {v.toFixed(1)}%
                                                    </span>
                                                </div>
                                                <div className="lb-event-midline" />
                                                <div
                                                    className={`lb-event-fill ${isUp ? "up" : "down"}`}
                                                    style={{ "--fill-h": fillH } as React.CSSProperties}
                                                />
                                            </div>
                                        );
                                    })}
                                </div>
                            )}

                            {/* Rules box */}
                            <div className="lb-rule-box">
                                <strong>{t("leaderboard.rankingRules")}</strong>
                                <span>{t("leaderboard.rule1")}</span>
                                <span>{t("leaderboard.rule2")}</span>
                                <span>{t("leaderboard.rule3")}</span>
                            </div>

                            {/* View run link */}
                            <Link
                                to={`/arena/submissions/${selected.submission_id}`}
                                className="lb-reset-btn"
                                style={{ textAlign: "center", display: "block", marginTop: "8px", textDecoration: "none", color: "inherit" }}
                            >
                                {t("leaderboard.viewRunDetails")}
                            </Link>
                        </>
                    ) : (
                        <div className="text-center p-8 text-[#555]">
                            {entries.length > 0 ? t("leaderboard.selectRow") : t("leaderboard.noDisplay")}
                        </div>
                    )}
                </aside>
            </section>
        </main>
    );
}
