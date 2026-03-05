import React from "react";
import { RunOut, SummaryOut } from "../lib/v4t";

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
    summary: SummaryOut | null;
}) {
    return (
        <article className="hero-card block">
            <div className="hero-meta">
                RESULT REPORT / {run?.model_key || "UNKNOWN"} / {fmtDate(run?.started_at ?? null)}
            </div>
            <div className="hero-title-row">
                <div className="score">
                    <div className="score-label">综合评分</div>
                    <div className="score-value">78</div>
                </div>
                <div className="persona">
                    <h1>交易人格: 交易之神</h1>
                    <p>宏观判断 + 重仓多头 + 深保证金 / 击败 92.4% 用户</p>
                    <div className="tags">
                        <span>人上人</span>
                        <span>高回撤容忍</span>
                        <span>低频高质量</span>
                    </div>
                </div>
            </div>
            <p className="hero-summary">
                {summary?.summary_text ||
                    "你的策略在 10 个标准化事件中表现出强趋势捕捉能力，在 Extreme-Up 与 Stable 行情中显著领先； 在极端下跌阶段暴露出止损响应偏慢的问题，建议降低单笔仓位并增加保护性对冲。"}
            </p>
        </article>
    );
}
