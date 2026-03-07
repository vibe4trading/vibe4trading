import React from "react";
import { RunOut } from "../lib/v4t";

function fmtDate(iso: string | null) {
    if (!iso) return "–";
    try {
        const d = new Date(iso);
        return d.toISOString().replace("T", " ").substring(0, 16);
    } catch {
        return iso;
    }
}

export function ReportHero({
    run,
    summary,
}: {
    run: RunOut | null;
    summary: string | null;
}) {
    return (
        <article className="hero-card block">
            <div className="hero-meta">
                RESULT REPORT / {run?.model_key || "UNKNOWN"} / {fmtDate(run?.started_at ?? null)}
            </div>
            <div className="hero-title-row">
                <div className="score">
                    <div className="score-label">Overall Score</div>
                    <div className="score-value">78</div>
                </div>
                <div className="persona">
                    <h1>Trading Persona: God of Trading</h1>
                    <p>Macro Conviction + Heavy Long + Deep Margin / Beats 92.4% of users</p>
                    <div className="tags">
                        <span>Elite</span>
                        <span>High DD Tolerance</span>
                        <span>Low Freq, High Quality</span>
                    </div>
                </div>
            </div>
            <p className="hero-summary">
                {summary ||
                    "Your strategy demonstrated strong trend-capture ability across 10 standardized events, significantly outperforming in Extreme-Up and Stable regimes. However, it exposed slow stop-loss response during extreme drawdowns — consider reducing per-trade position sizing and adding protective hedges."}
            </p>
        </article>
    );
}
