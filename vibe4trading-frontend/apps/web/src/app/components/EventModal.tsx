import React from "react";
import { EventData } from "../lib/report-data";

export function EventModal({
    isOpen,
    onClose,
    eventData,
    eventCode,
}: {
    isOpen: boolean;
    onClose: () => void;
    eventData: EventData | null;
    eventCode: string;
}) {
    if (!isOpen || !eventData) return null;

    return (
        <div className="event-modal" onClick={onClose}>
            <article
                className="event-modal-panel"
                onClick={(e) => e.stopPropagation()}
            >
                <header className="event-modal-head">
                    <div className="modal-head-main">
                        <div className="modal-head-title-row">
                            <span className="event-code-chip">{eventCode}</span>
                            <h3>{eventData.title}</h3>
                        </div>
                        <p>{eventData.subtitle}</p>
                    </div>
                    <div className="modal-tag-row">
                        <span className="modal-tag tone-strong">
                            环境难度: {eventData.difficulty}
                        </span>
                        <span className="modal-tag tone-avg">
                            特征: {eventData.regime}
                        </span>
                        <span
                            className={`modal-tag ${eventData.edge === "Strong"
                                    ? "tone-strong"
                                    : eventData.edge === "Weak"
                                        ? "tone-weak"
                                        : "tone-avg"
                                }`}
                        >
                            模型优势: {eventData.edge}
                        </span>
                    </div>
                    <button className="modal-close-btn" onClick={onClose}>
                        [ESC] 关闭
                    </button>
                </header>

                <div className="event-modal-body">
                    <section className="event-modal-left">
                        <div className="modal-card story-card">
                            <h4>事件剧情 / Storyline</h4>
                            <p className="story-subtitle">{eventData.period}</p>
                            <p style={{ fontSize: "14px", lineHeight: 1.5 }}>
                                {eventData.background}
                            </p>
                        </div>

                        <div className="modal-card">
                            <div className="modal-card-head">
                                <h4>净值回放 / Equity Curve</h4>
                                <span>{eventData.period}</span>
                            </div>
                            <div className="curve-meta-strip">
                                <span>标的: BTC-USDT</span>
                                <span>基准: $1,000</span>
                                <span>最大连转: 2</span>
                            </div>

                            <svg
                                viewBox="0 0 600 220"
                                className="modal-curve-svg"
                                preserveAspectRatio="none"
                                style={{ height: "200px" }}
                            >
                                <g className="chart-grid">
                                    <line x1="0" y1="40" x2="600" y2="40" />
                                    <line x1="0" y1="80" x2="600" y2="80" />
                                    <line x1="0" y1="120" x2="600" y2="120" />
                                    <line x1="0" y1="160" x2="600" y2="160" />
                                </g>
                                <line x1="0" y1="180" x2="600" y2="180" className="volume-base" />

                                {eventData.curve.map((val, i) => {
                                    const x = (i / (eventData.curve.length - 1)) * 580 + 10;
                                    const isUp = val > (eventData.curve[i - 1] || val);
                                    return (
                                        <rect
                                            key={`v-${i}`}
                                            x={x - 8}
                                            y={isUp ? 185 : 190}
                                            width="16"
                                            height={isUp ? 35 : 30}
                                            className={`vol-bar ${isUp ? "up" : "down"}`}
                                        />
                                    );
                                })}

                                <path
                                    d={`M 10 220 L 10 ${220 - eventData.curve[0]} ${eventData.curve
                                        .map((v, i) => {
                                            const x = (i / (eventData.curve.length - 1)) * 580 + 10;
                                            return `L ${x} ${220 - v}`;
                                        })
                                        .join(" ")} L 590 220 Z`}
                                    className={`modal-curve-area ${eventData.curve[eventData.curve.length - 1] > eventData.curve[0]
                                            ? "pos"
                                            : "neg"
                                        }`}
                                />
                                <path
                                    d={`M ${eventData.curve
                                        .map((v, i) => {
                                            const x = (i / (eventData.curve.length - 1)) * 580 + 10;
                                            return `${x},${220 - v}`;
                                        })
                                        .join(" L ")}`}
                                    className={`modal-curve-line ${eventData.curve[eventData.curve.length - 1] > eventData.curve[0]
                                            ? "pos"
                                            : "neg"
                                        }`}
                                />

                                {eventData.curve.map((v, i) => {
                                    const x = (i / (eventData.curve.length - 1)) * 580 + 10;
                                    return (
                                        <circle
                                            key={`d-${i}`}
                                            cx={x}
                                            cy={220 - v}
                                            r="4"
                                            className="modal-dot base-dot"
                                        />
                                    );
                                })}
                            </svg>
                        </div>
                    </section>

                    <section className="event-modal-right">
                        <div className="modal-card">
                            <h4>表现指标 / Event Stats</h4>
                            <div className="modal-stat-grid">
                                <div style={{ padding: "8px", background: "#eaeaea" }}>
                                    <div style={{ fontSize: "11px", color: "#666", marginBottom: "4px" }}>
                                        RETURN
                                    </div>
                                    <div
                                        style={{
                                            fontSize: "18px",
                                            fontWeight: "bold",
                                            color: eventData.metrics.ret.startsWith("-")
                                                ? "var(--red)"
                                                : "var(--green)",
                                        }}
                                    >
                                        {eventData.metrics.ret}
                                    </div>
                                </div>
                                <div style={{ padding: "8px", background: "#f0f0f0" }}>
                                    <div style={{ fontSize: "11px", color: "#666", marginBottom: "4px" }}>
                                        WIN RATE
                                    </div>
                                    <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                                        {eventData.metrics.win}
                                    </div>
                                </div>
                                <div style={{ padding: "8px", background: "#f0f0f0" }}>
                                    <div style={{ fontSize: "11px", color: "#666", marginBottom: "4px" }}>
                                        MAX DD
                                    </div>
                                    <div style={{ fontSize: "16px", fontWeight: "bold", color: "var(--red)" }}>
                                        {eventData.metrics.dd}
                                    </div>
                                </div>
                                <div style={{ padding: "8px", background: "#f0f0f0" }}>
                                    <div style={{ fontSize: "11px", color: "#666", marginBottom: "4px" }}>
                                        PRFT.FCT
                                    </div>
                                    <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                                        {eventData.metrics.pf}
                                    </div>
                                </div>
                                <div style={{ padding: "8px", background: "#f0f0f0" }}>
                                    <div style={{ fontSize: "11px", color: "#666", marginBottom: "4px" }}>
                                        TRADES
                                    </div>
                                    <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                                        {eventData.metrics.trades}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="modal-card" style={{ flexGrow: 1 }}>
                            <div className="modal-card-head">
                                <h4>关键决策 / Key Nodes</h4>
                            </div>
                            <div style={{ display: "grid", gap: "8px" }}>
                                {eventData.nodes.map((node, i) => {
                                    const isWin = node.r.startsWith("+");
                                    const isLoss = node.r.startsWith("-");
                                    return (
                                        <div
                                            key={i}
                                            style={{
                                                padding: "8px",
                                                border: "1px solid #ccc",
                                                background: "#fff",
                                                display: "flex",
                                                gap: "12px",
                                                alignItems: "flex-start",
                                            }}
                                        >
                                            <div
                                                style={{
                                                    background: "#e4e4e4",
                                                    padding: "4px",
                                                    fontSize: "10px",
                                                    fontFamily: "monospace",
                                                    minWidth: "85px",
                                                }}
                                            >
                                                {node.t}
                                            </div>
                                            <div style={{ flex: 1 }}>
                                                <div style={{ fontWeight: "bold", fontSize: "14px", marginBottom: "2px" }}>
                                                    {node.a}
                                                </div>
                                                <div style={{ fontSize: "12px", color: "#555" }}>
                                                    {node.l}
                                                </div>
                                            </div>
                                            <div
                                                style={{
                                                    fontWeight: "bold",
                                                    fontSize: "14px",
                                                    color: isWin ? "var(--green)" : isLoss ? "var(--red)" : "inherit",
                                                }}
                                            >
                                                {node.r}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </section>
                </div>
            </article>
        </div>
    );
}
