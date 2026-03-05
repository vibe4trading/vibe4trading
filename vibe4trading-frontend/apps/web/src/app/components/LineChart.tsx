"use client";

import * as React from "react";

type Point = {
  xLabel: string;
  y: number;
};

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

export function LineChart({
  points,
  height = 180,
  title = "Equity",
  ariaLabel,
  strokeFrom = "rgba(20,184,166,0.95)",
  strokeTo = "rgba(249,115,22,0.85)",
  markers,
}: {
  points: Point[];
  height?: number;
  title?: string;
  ariaLabel?: string;
  strokeFrom?: string;
  strokeTo?: string;
  markers?: { index: number; color?: string; label?: string }[];
}) {
  const id = React.useId();
  const safeId = id.replace(/[^a-zA-Z0-9_-]/g, "_");
  const gradId = `v4tLineGrad-${safeId}`;
  const fillGradId = `v4tLineFill-${safeId}`;

  const width = 640;
  const padding = 14;

  const ys = points.map((p) => p.y);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanY = Math.max(1e-9, maxY - minY);

  const toX = (i: number) => {
    if (points.length <= 1) return padding;
    const t = i / (points.length - 1);
    return padding + t * (width - padding * 2);
  };
  const toY = (y: number) => {
    const t = (y - minY) / spanY;
    return padding + (1 - t) * (height - padding * 2);
  };

  const d = points
    .map((p, i) => {
      const x = toX(i);
      const y = toY(p.y);
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");

  const last = points[points.length - 1];
  const lastY = last ? last.y : 0;
  const lastPct = points.length > 0 && points[0].y !== 0 ? ((lastY - points[0].y) / points[0].y) * 100 : 0;

  const fillD = points.length > 0
    ? `${d} L${toX(points.length - 1).toFixed(2)} ${(height - padding).toFixed(2)} L${toX(0).toFixed(2)} ${(height - padding).toFixed(2)} Z`
    : "";

  return (
    <div className="w-full overflow-hidden rounded-2xl border border-[color:var(--border)] bg-white/5 shadow-lg backdrop-blur-md">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="text-sm font-medium text-white">{title}</div>
        <div className="text-xs text-zinc-400">
          <span className="font-mono">{lastY.toFixed(2)}</span>
          <span className="mx-2 text-zinc-600">/</span>
          <span
            className={
              lastPct >= 0 ? "text-[color:var(--accent)] drop-shadow-[0_0_6px_var(--accent-glow)]" : "text-rose-400"
            }
          >
            {lastPct >= 0 ? "+" : ""}
            {isFinite(lastPct) ? lastPct.toFixed(2) : "0.00"}%
          </span>
        </div>
      </div>

      <div className="px-3 pb-3">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-[180px] w-full"
          role="img"
          aria-label={ariaLabel ?? `${title} line chart`}
        >
          <defs>
            <linearGradient id={gradId} x1="0" x2="1" y1="0" y2="0">
              <stop offset="0" stopColor={strokeFrom} />
              <stop offset="1" stopColor={strokeTo} />
            </linearGradient>
            <linearGradient id={fillGradId} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor={strokeFrom} stopOpacity="0.15" />
              <stop offset="1" stopColor={strokeFrom} stopOpacity="0" />
            </linearGradient>
          </defs>

          <rect
            x={0}
            y={0}
            width={width}
            height={height}
            fill="rgba(255,255,255,0.0)"
          />

          {/* faint grid */}
          {[0.25, 0.5, 0.75].map((t) => {
            const y = padding + t * (height - padding * 2);
            return (
              <line
                key={t}
                x1={padding}
                x2={width - padding}
                y1={y}
                y2={y}
                stroke="rgba(255,255,255,0.06)"
                strokeWidth={1}
              />
            );
          })}

          {points.length > 0 ? (
            <>
              {markers
                ? markers
                    .filter((m) => m.index >= 0 && m.index < points.length)
                    .map((m) => {
                      const x = toX(m.index);
                      const c = m.color ?? "rgba(255,255,255,0.22)";
                      return (
                        <g key={`${m.index}:${m.label ?? ""}`}>
                          <line
                            x1={x}
                            x2={x}
                            y1={padding}
                            y2={height - padding}
                            stroke={c}
                            strokeWidth={1}
                            strokeDasharray="3 5"
                          />
                          <circle
                            cx={x}
                            cy={toY(points[m.index].y)}
                            r={3.25}
                            fill={c}
                            stroke="rgba(0,0,0,0.35)"
                            strokeWidth={1}
                          />
                          {m.label ? (
                            <text
                              x={x + 6}
                              y={padding + 12}
                              fill={c}
                              fontSize={10}
                            >
                              {m.label}
                            </text>
                          ) : null}
                        </g>
                      );
                    })
                : null}
              <path d={fillD} fill={`url(#${fillGradId})`} />
              <path
                d={d}
                fill="none"
                stroke={`url(#${gradId})`}
                strokeWidth={2.25}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              <circle
                cx={toX(points.length - 1)}
                cy={toY(lastY)}
                r={4}
                fill="rgba(255,255,255,0.92)"
                stroke="rgba(255,255,255,0.3)"
                strokeWidth={2}
              />
            </>
          ) : (
            <text x={padding} y={padding + 12} fill="rgba(255,255,255,0.4)" fontSize={12}>
              No data yet
            </text>
          )}

          {/* clamped bounds to avoid text overlap */}
          {points.length > 0 ? (
            <text
              x={padding}
              y={clamp(toY(maxY) - 6, 12, height - 6)}
              fill="rgba(255,255,255,0.4)"
              fontSize={11}
            >
              {maxY.toFixed(2)}
            </text>
          ) : null}
          {points.length > 0 ? (
            <text
              x={padding}
              y={clamp(toY(minY) + 14, 12, height - 6)}
              fill="rgba(255,255,255,0.4)"
              fontSize={11}
            >
              {minY.toFixed(2)}
            </text>
          ) : null}
        </svg>

        <div className="mt-2 flex justify-between text-xs text-zinc-500">
          <span className="font-mono">{points[0]?.xLabel ?? ""}</span>
          <span className="font-mono">{points[points.length - 1]?.xLabel ?? ""}</span>
        </div>
      </div>
    </div>
  );
}
