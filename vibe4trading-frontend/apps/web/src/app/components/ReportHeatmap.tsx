import React from "react";
import { heatmapData } from "../lib/report-data";

export function ReportHeatmap({
    activeEvent,
    highlightedEvent,
    onEventHover,
    onEventClick,
}: {
    activeEvent: string | null;
    highlightedEvent: string | null;
    onEventHover: (code: string | null) => void;
    onEventClick: (code: string) => void;
}) {
    return (
        <aside className="right-column">
            <section className="heatlog-panel">
                <header className="heatlog-header">
                    <div>EVENT PERFORMANCE HEATMAP</div>
                </header>

                <div className="heatlog-col-head">
                    <span>EVENT</span>
                    <span>RETURN %</span>
                    <span>WIN RATE</span>
                    <span>MAX DD</span>
                    <span>PROFIT FACTOR</span>
                    <span>#TRADES</span>
                </div>

                {heatmapData.map((item) => {
                    const isActive = activeEvent === item.event;
                    const isHighlighted = highlightedEvent === item.event;

                    return (
                        <article
                            key={item.event}
                            className={`heatlog-row ${isActive ? "is-active" : ""}`}
                            data-event={item.event}
                            role="button"
                            tabIndex={0}
                            onClick={() => onEventClick(item.event)}
                            onMouseEnter={() => onEventHover(item.event)}
                            onMouseLeave={() => onEventHover(null)}
                            style={{
                                outline: isHighlighted && !isActive ? "2px solid #a0a0a0" : undefined,
                                outlineOffset: isHighlighted && !isActive ? "-2px" : undefined,
                            }}
                        >
                            <div className="event-cell">
                                <span className={`event-mark ${item.mark}`}>
                                    {item.mark === "warn" ? "!" : item.mark === "crash" ? "X" : ""}
                                </span>
                                <div>
                                    <strong>{item.event}</strong>
                                    <p>{item.name}</p>
                                </div>
                            </div>
                            <div className={`metric-cell ${item.mark === "strong" ? "strong" : item.mark === "avg" ? "avg" : item.mark === "weak" ? "weak" : ""}`}>
                                {item.ret}
                            </div>
                            <div className={`metric-cell ${item.mark === "strong" ? "strong" : item.mark === "avg" ? "avg" : item.mark === "weak" ? "weak" : ""}`}>
                                {item.win}
                            </div>
                            <div className={`metric-cell ${item.mark === "strong" ? "strong" : item.mark === "avg" ? "avg" : item.mark === "weak" ? "weak" : ""}`}>
                                {item.dd}
                            </div>
                            <div className={`metric-cell ${item.mark === "strong" ? "strong" : item.mark === "avg" ? "avg" : item.mark === "weak" ? "weak" : ""}`}>
                                {item.pf}
                            </div>
                            <div className="trades-cell">{item.trades}</div>
                        </article>
                    );
                })}

                <footer className="heatlog-legend">
                    <span>
                        <i className="lg strong"></i>Strong
                    </span>
                    <span>
                        <i className="lg avg"></i>Average
                    </span>
                    <span>
                        <i className="lg weak"></i>Weak
                    </span>
                </footer>
            </section>
        </aside>
    );
}
