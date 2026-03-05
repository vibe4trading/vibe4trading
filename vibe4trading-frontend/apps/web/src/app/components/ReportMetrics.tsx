import React from "react";

export function ReportMetrics() {
    return (
        <section className="metric-grid">
            <article className="metric block">
                <h3>总收益率</h3>
                <p className="value positive">+10.67%</p>
                <p className="rank good">评级: 夯</p>
            </article>
            <article className="metric block">
                <h3>胜率</h3>
                <p className="value positive">63.0%</p>
                <p className="rank elite">评级: 人上人</p>
            </article>
            <article className="metric block">
                <h3>最大回撤</h3>
                <p className="value negative">12.4%</p>
                <p className="rank mid">评级: NPC</p>
            </article>
            <article className="metric block">
                <h3>夏普指数</h3>
                <p className="value positive">1.42</p>
                <p className="rank elite">评级: 人上人</p>
            </article>
            <article className="metric block">
                <h3>杠杆均值</h3>
                <p className="value neutral">3.0x</p>
                <p className="rank bad">评级: 拉完了</p>
            </article>
        </section>
    );
}
