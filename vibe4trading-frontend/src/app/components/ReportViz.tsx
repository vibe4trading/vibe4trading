import React from "react";
import { RunOut } from "../lib/v4t";

export function ReportViz({
    run,
    highlightedEvent,
    onEventHover,
    onEventClick,
}: {
    run: RunOut | null;
    highlightedEvent: string | null;
    onEventHover: (code: string | null) => void;
    onEventClick: (code: string) => void;
}) {
    const barData = [
        { event: "W01", value: -4.2, label: "-4.2%" },
        { event: "W02", value: 2.1, label: "+2.1%" },
        { event: "W03", value: 5.9, label: "+5.9%" },
        { event: "W04", value: 9.8, label: "+9.8%" },
        { event: "W05", value: 4.3, label: "+4.3%" },
        { event: "W06", value: 3.0, label: "+3.0%" },
        { event: "W07", value: -6.9, label: "-6.9%" },
        { event: "W08", value: -2.7, label: "-2.7%" },
        { event: "W09", value: 4.9, label: "+4.9%" },
        { event: "W10", value: -10.4, label: "-10.4%" },
    ];

    const getBarY = (value: number) => {
        const scale = 104 / 20;
        return 130 - value * scale;
    };

    const getBarHeight = (value: number) => {
        const scale = 104 / 20;
        return Math.abs(value) * scale;
    };

    return (
        <section className="viz-grid">
            <article className="block chart-card">
                <header>
                    <h2>10时间段收益率对比 / Return Bars</h2>
                    <span>
                        模型: {run?.model_key || "GPT-5.1"} ｜ 虚拟币: {run?.market_id || "BTC/USDT"} ｜ 报告模式: HISTORICAL ｜ Starting balance: 1000 USDT
                    </span>
                </header>
                <svg
                    viewBox="0 0 640 260"
                    className="bar-chart"
                    aria-label="ten-window-returns"
                >
                    <rect x="0" y="0" width="640" height="260" fill="#f7f7f5"></rect>
                    <line x1="30" y1="30" x2="30" y2="234" className="axis-line"></line>
                    <line x1="30" y1="234" x2="624" y2="234" className="axis-line"></line>
                    <line x1="30" y1="130" x2="624" y2="130" className="zero-line"></line>

                    <text x="6" y="35" className="y-tick">
                        +10%
                    </text>
                    <text x="8" y="134" className="y-tick">
                        0%
                    </text>
                    <text x="6" y="230" className="y-tick">
                        -10%
                    </text>

                    {barData.map((bar, i) => {
                        const x = 44 + i * 58;
                        const isNegative = bar.value < 0;
                        const barY = isNegative ? 130 : getBarY(bar.value);
                        const barHeight = getBarHeight(bar.value);
                        const isDim = highlightedEvent && highlightedEvent !== bar.event;

                        return (
                            <g
                                key={bar.event}
                                className={isDim ? "bar-item dim" : "bar-item"}
                                data-event={bar.event}
                                style={{ cursor: "pointer" }}
                                onMouseEnter={() => onEventHover(bar.event)}
                                onMouseLeave={() => onEventHover(null)}
                                onClick={() => onEventClick(bar.event)}
                            >
                                <rect
                                    x={x}
                                    y={barY}
                                    width="42"
                                    height={barHeight}
                                    className={isNegative ? "bar-neg" : "bar-pos"}
                                />
                                <text
                                    x={x + 4}
                                    y={isNegative ? barY + barHeight + 14 : barY - 7}
                                    className="bar-value"
                                >
                                    {bar.label}
                                </text>
                                <text x={x + 8} y="250" className="bar-label">
                                    {bar.event}
                                </text>
                            </g>
                        );
                    })}
                </svg>
            </article>

            <article className="block chart-card">
                <header>
                    <h2>能力雷达 / Radar</h2>
                    <span>6 维能力六边形</span>
                </header>
                <svg viewBox="0 0 320 220" className="radar-chart" aria-label="radar">
                    <polygon
                        points="160,28 248,78 248,162 160,212 72,162 72,78"
                        fill="#e4e6f0"
                        stroke="#2f3036"
                        strokeWidth="2"
                    ></polygon>
                    <polygon
                        points="160,52 222,88 214,148 160,178 100,152 106,84"
                        fill="#91a8ff99"
                        stroke="#3c5ef0"
                        strokeWidth="3"
                    ></polygon>
                    <line x1="160" y1="28" x2="160" y2="212" stroke="#777" />
                    <line x1="72" y1="78" x2="248" y2="162" stroke="#777" />
                    <line x1="248" y1="78" x2="72" y2="162" stroke="#777" />
                </svg>
                <div className="radar-legend">
                    <span>趋势捕捉 86</span>
                    <span>风控纪律 58</span>
                    <span>择时能力 72</span>
                    <span>回撤控制 54</span>
                    <span>稳定性 68</span>
                    <span>决策清晰度 80</span>
                </div>
            </article>
        </section>
    );
}
