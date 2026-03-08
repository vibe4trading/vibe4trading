import { Link } from "react-router-dom";
import * as React from "react";
import {
    apiJson,
    LeaderboardEntryOut,
    ModelPublicOut,
    ScenarioSetOut,
} from "@/app/lib/v4t";

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
        }
    }, [modelFilter, marketFilter]);

    React.useEffect(() => {
        const timer = setTimeout(() => { refresh(); }, 300);
        return () => clearTimeout(timer);
    }, [refresh]);

    const selected = entries.find((e) => e.submission_id === selectedId) ?? null;
    const selectedRank = selected ? entries.indexOf(selected) + 1 : 0;

    const topPnl = entries.length > 0 ? entries[0] : null;

    return (
        <main className="leaderboard-page-main animate-rise">
            {/* PAGE HEADER */}
            <section className="leaderboard-screen-head block">
                <div className="lb-title-line">
                    <h1>LEADERBOARD</h1>
                    <div className="lb-live-status">
                        <i className="live-dot" />
                        <strong>Historical Ranking</strong>
                        <em>--:--</em>
                    </div>
                </div>
                <p>
                    Ranking based on composite PnL across historical events. Tiebreakers: Sharpe, then Max DD. Each filter shows up to Top 100.
                </p>

                <div className="lb-filter-grid">
                    <label>
                        Model
                        <select
                            value={modelFilter}
                            onChange={(e) => setModelFilter(e.target.value)}
                        >
                            <option value="ALL">ALL MODELS</option>
                            {models.map((m) => (
                                <option key={m.model_key} value={m.model_key}>
                                    {m.label ? `${m.label} (${m.model_key})` : m.model_key}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label>
                        Pair
                        <select
                            value={marketFilter}
                            onChange={(e) => setMarketFilter(e.target.value)}
                        >
                            <option value="ALL">ALL PAIRS</option>
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
            <section className="lb-kpi-grid">
                <article className="lb-kpi-card">
                    <span>Filtered Results</span>
                    <strong>{entries.length}</strong>
                    <em>Current filter shows up to Top 100</em>
                </article>
                <article className="lb-kpi-card">
                    <span>Top 1 PnL (Filtered)</span>
                    <strong className={pctClass(topPnl?.total_return_pct)}>
                        {topPnl ? pct(topPnl.total_return_pct) : "\u2013"}
                    </strong>
                    <em>{topPnl?.model_key ?? "\u2013"}</em>
                </article>
                <article className="lb-kpi-card">
                    <span>Top 1 Sharpe</span>
                    <strong>{topPnl ? stat(topPnl.sharpe_ratio) : "\u2013"}</strong>
                    <em>Risk-adjusted return</em>
                </article>
                <article className="lb-kpi-card">
                    <span>Top 1 Max DD</span>
                    <strong>{topPnl ? `${stat(topPnl.max_drawdown_pct)}%` : "\u2013"}</strong>
                    <em>Worst peak-to-trough</em>
                </article>
            </section>

            {/* TABLE + SIDE PANEL */}
            <section className="lb-main-grid">
                {/* LEFT: TABLE */}
                <section className="leaderboard-proto block">
                    <header className="lb-head">
                        <div>
                            <h2>Vibe4Trading · TOP 100</h2>
                            <p>Top models sorted by PnL. Displays up to top 100 based on filters.</p>
                        </div>
                        <div className="lb-head-metrics">
                            <span>START BALANCE: {initialEquity != null ? `${initialEquity.toLocaleString()} USDT` : "–"}</span>
                            <span>ENTRIES: {entries.length}</span>
                            <span>UPDATED: Live</span>
                        </div>
                    </header>

                    <div className="lb-scroll-shell">
                        <div className="lb-row lb-row-head">
                            <span>RANK</span>
                            <span>MODEL</span>
                            <span>PAIR</span>
                            <span>PNL</span>
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
                                <div className="text-center p-8 text-[#555]">No entries found.</div>
                            )}
                            {refreshing && (
                                <div className="text-center p-8 text-[#555]">Loading...</div>
                            )}
                        </div>
                    </div>
                </section>

                {/* RIGHT: SIDE PANEL */}
                <aside className="lb-side-panel block">
                    {selected ? (
                        <>
                            <h3>Strategy Details</h3>

                            <div className="lb-selected-meta">
                                <strong>
                                    #{String(selectedRank).padStart(3, "0")} · {selected.model_key}
                                </strong>
                                <p>{pairName(selected.market_id)}</p>
                                <p>Top 100 live comparison (PnL priority)</p>
                            </div>

                            {/* Stats grid 2x3 */}
                            <div className="lb-selected-stat-grid">
                                <div className="lb-selected-stat">
                                    <span>Total PnL</span>
                                    <strong className={pctClass(selected.total_return_pct)}>
                                        {pct(selected.total_return_pct)}
                                    </strong>
                                </div>
                                <div className="lb-selected-stat">
                                    <span>Win Rate</span>
                                    <strong>
                                        {selected.win_rate_pct != null
                                            ? `${stat(selected.win_rate_pct, 1)}%`
                                            : "\u2013"}
                                    </strong>
                                </div>
                                <div className="lb-selected-stat">
                                    <span>Sharpe</span>
                                    <strong>{stat(selected.sharpe_ratio)}</strong>
                                </div>
                                <div className="lb-selected-stat">
                                    <span>Profit Factor</span>
                                    <strong>{stat(selected.profit_factor)}</strong>
                                </div>
                                <div className="lb-selected-stat">
                                    <span>Max DD</span>
                                    <strong>
                                        {selected.max_drawdown_pct != null
                                            ? `${stat(selected.max_drawdown_pct, 1)}%`
                                            : "\u2013"}
                                    </strong>
                                </div>
                                <div className="lb-selected-stat">
                                    <span>#Trades</span>
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
                                <strong>Ranking Rules</strong>
                                <span>1. Default ranking by composite PnL across events</span>
                                <span>2. Tiebreaker: Sharpe first, then Max DD (lower is better)</span>
                                <span>3. Each model/pair filter shows up to Top 100</span>
                            </div>

                            {/* View run link */}
                            <Link
                                to={`/arena/submissions/${selected.submission_id}`}
                                className="lb-reset-btn"
                                style={{ textAlign: "center", display: "block", marginTop: "8px", textDecoration: "none", color: "inherit" }}
                            >
                                VIEW RUN DETAILS →
                            </Link>
                        </>
                    ) : (
                        <div className="text-center p-8 text-[#555]">
                            {entries.length > 0 ? "Select a row to view details" : "No entries to display"}
                        </div>
                    )}
                </aside>
            </section>
        </main>
    );
}
