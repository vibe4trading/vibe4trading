import React from "react";

export function ReportMetrics() {
    return (
        <section className="metric-grid">
            <article className="metric block">
                <h3>Total Return</h3>
                <p className="value positive">+10.67%</p>
                <p className="rank good">Rank: Solid</p>
            </article>
            <article className="metric block">
                <h3>Win Rate</h3>
                <p className="value positive">63.0%</p>
                <p className="rank elite">Rank: Elite</p>
            </article>
            <article className="metric block">
                <h3>Max Drawdown</h3>
                <p className="value negative">12.4%</p>
                <p className="rank mid">Rank: Average</p>
            </article>
            <article className="metric block">
                <h3>Sharpe Ratio</h3>
                <p className="value positive">1.42</p>
                <p className="rank elite">Rank: Elite</p>
            </article>
            <article className="metric block">
                <h3>Avg Leverage</h3>
                <p className="value neutral">3.0x</p>
                <p className="rank bad">Rank: Rekt</p>
            </article>
        </section>
    );
}
