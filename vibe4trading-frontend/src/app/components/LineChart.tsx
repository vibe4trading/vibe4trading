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
  variant = "dark",
  showBaseline = true,
}: {
  points: Point[];
  height?: number;
  title?: string;
  ariaLabel?: string;
  strokeFrom?: string;
  strokeTo?: string;
  markers?: { index: number; color?: string; label?: string }[];
  variant?: "dark" | "light";
  showBaseline?: boolean;
}) {
  const id = React.useId();
  const safeId = id.replace(/[^a-zA-Z0-9_-]/g, "_");
  const gradId = `v4tLineGrad-${safeId}`;
  const fillGradId = `v4tLineFill-${safeId}`;

  const width = 640;
  const padding = 14;

  const ys = points.map((p) => p.y);
  const minY = ys.length > 0 ? Math.min(...ys) : 0;
  const maxY = ys.length > 0 ? Math.max(...ys) : 1;
  const spanY = Math.max(1e-9, maxY - minY);

  /* ── padded Y range (8% breathing room) ── */
  const paddedMin = minY - spanY * 0.08;
  const paddedMax = maxY + spanY * 0.08;
  const paddedSpan = Math.max(1e-9, paddedMax - paddedMin);
  const rightPad = 56;

  /* ── flat-data detection ── */
  const meanY =
    ys.length > 0 ? ys.reduce((a, b) => a + b, 0) / ys.length : 0;
  const isFlat =
    ys.length > 0 &&
    Math.abs(meanY) > 1e-12 &&
    spanY < 0.001 * Math.abs(meanY);
  const yDecimals = isFlat
    ? Math.min(
        6,
        Math.max(
          4,
          Math.ceil(-Math.log10(spanY / Math.abs(meanY))) + 2,
        ),
      )
    : 2;
  const formatYVal = (v: number) => v.toFixed(yDecimals);

  /* ── percentage helpers ── */
  const firstY = points.length > 0 ? points[0].y : 0;
  const pctAt = (v: number) =>
    firstY !== 0 ? ((v - firstY) / firstY) * 100 : 0;
  const formatPct = (v: number) =>
    `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
  const midY = (minY + maxY) / 2;

  const isLight = variant === "light";
  const cardClass = isLight
    ? "w-full overflow-hidden border-2 border-[var(--line)] bg-[#fbfbf8] shadow-[6px_6px_0_rgba(0,0,0,0.08)]"
    : "w-full overflow-hidden rounded-2xl border border-[color:var(--border)] bg-white/5 shadow-lg backdrop-blur-md";
  const titleClass = isLight ? "text-sm font-medium text-[var(--ink)]" : "text-sm font-medium text-white";
  const metaClass = isLight ? "text-xs text-[var(--muted)]" : "text-xs text-zinc-400";
  const positivePctClass = isLight ? "text-[var(--green)]" : "text-[color:var(--accent)] drop-shadow-[0_0_6px_var(--accent-glow)]";
  const gridStroke = isLight ? "rgba(0,0,0,0.09)" : "rgba(255,255,255,0.06)";
  const emptyTextFill = isLight ? "rgba(0,0,0,0.45)" : "rgba(255,255,255,0.4)";
  const axisLabelFill = isLight ? "rgba(0,0,0,0.5)" : "rgba(255,255,255,0.4)";
  const markerStroke = isLight ? "rgba(0,0,0,0.2)" : "rgba(0,0,0,0.35)";
  const markerFill = isLight ? "rgba(0,0,0,0.92)" : "rgba(255,255,255,0.92)";
  const footerClass = isLight ? "mt-2 flex justify-between text-xs text-[var(--muted)]" : "mt-2 flex justify-between text-xs text-zinc-500";

  const toX = React.useCallback((i: number) => {
    if (points.length <= 1) return padding;
    const t = i / (points.length - 1);
    return padding + t * (width - padding - rightPad);
  }, [points.length, padding, rightPad, width]);

  const toY = React.useCallback((y: number) => {
    const t = (y - paddedMin) / paddedSpan;
    return padding + (1 - t) * (height - padding * 2);
  }, [paddedMin, paddedSpan, padding, height]);

  const d = React.useMemo(() => points
    .map((p, i) => {
      const x = toX(i);
      const y = toY(p.y);
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" "), [points, toX, toY]);

  const last = points[points.length - 1];
  const lastY = last ? last.y : 0;
  const lastPct = points.length > 0 && points[0].y !== 0 ? ((lastY - points[0].y) / points[0].y) * 100 : 0;

  const fillD = React.useMemo(() => points.length > 0
    ? `${d} L${toX(points.length - 1).toFixed(2)} ${(height - padding).toFixed(2)} L${toX(0).toFixed(2)} ${(height - padding).toFixed(2)} Z`
    : "", [d, points.length, toX, height, padding]);

  return (
    <div className={cardClass}>
      <div className="flex items-center justify-between px-4 py-3">
        <div className={titleClass}>{title}</div>
        <div className={metaClass}>
          <span className="font-mono">{lastY.toFixed(2)}</span>
          <span className="mx-2 text-zinc-600">/</span>
          <span
            className={lastPct >= 0 ? positivePctClass : "text-rose-400"}
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
                x2={width - rightPad}
                y1={y}
                y2={y}
                stroke={gridStroke}
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
                            stroke={markerStroke}
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
              {showBaseline && points.length > 1 && (
                <g>
                  <line
                    x1={padding}
                    x2={width - rightPad}
                    y1={toY(firstY)}
                    y2={toY(firstY)}
                    stroke={isLight ? "rgba(0,0,0,0.18)" : "rgba(255,255,255,0.15)"}
                    strokeWidth={1}
                    strokeDasharray="5 4"
                  />
                  <text
                    x={width - rightPad + 4}
                    y={toY(firstY) + 3}
                    fill={isLight ? "rgba(0,0,0,0.32)" : "rgba(255,255,255,0.28)"}
                    fontSize={9}
                    fontStyle="italic"
                  >
                    start {formatYVal(firstY)}
                  </text>
                </g>
              )}
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
                fill={markerFill}
                stroke={isLight ? "rgba(0,0,0,0.16)" : "rgba(255,255,255,0.3)"}
                strokeWidth={2}
              />
            </>
          ) : (
            <text x={padding} y={padding + 12} fill={emptyTextFill} fontSize={12}>
              No data yet
            </text>
          )}

          {points.length > 0 ? (
            <>
              <text
                x={padding}
                y={clamp(toY(maxY) - 6, 12, height - 6)}
                fill={axisLabelFill}
                fontSize={10}
              >
                {formatYVal(maxY)}
              </text>
              <text
                x={width - 4}
                y={clamp(toY(maxY) - 6, 12, height - 6)}
                fill={axisLabelFill}
                fontSize={9.5}
                textAnchor="end"
                fontFamily="monospace"
              >
                {formatPct(pctAt(maxY))}
              </text>

              <text
                x={padding}
                y={clamp(toY(midY) + 4, 12, height - 6)}
                fill={axisLabelFill}
                fontSize={10}
              >
                {formatYVal(midY)}
              </text>
              <text
                x={width - 4}
                y={clamp(toY(midY) + 4, 12, height - 6)}
                fill={axisLabelFill}
                fontSize={9.5}
                textAnchor="end"
                fontFamily="monospace"
              >
                {formatPct(pctAt(midY))}
              </text>

              <text
                x={padding}
                y={clamp(toY(minY) + 14, 12, height - 6)}
                fill={axisLabelFill}
                fontSize={10}
              >
                {formatYVal(minY)}
              </text>
              <text
                x={width - 4}
                y={clamp(toY(minY) + 14, 12, height - 6)}
                fill={axisLabelFill}
                fontSize={9.5}
                textAnchor="end"
                fontFamily="monospace"
              >
                {formatPct(pctAt(minY))}
              </text>

              {isFlat && (
                <text
                  x={(padding + width - rightPad) / 2}
                  y={height / 2 + 24}
                  fill={isLight ? "rgba(0,0,0,0.22)" : "rgba(255,255,255,0.18)"}
                  fontSize={10}
                  textAnchor="middle"
                  fontStyle="italic"
                >
                  &lt; 0.1% range
                </text>
              )}
            </>
          ) : null}
        </svg>

        <div className={footerClass}>
          <span className="font-mono">{points[0]?.xLabel ?? ""}</span>
          <span className="font-mono">{points[points.length - 1]?.xLabel ?? ""}</span>
        </div>
      </div>
    </div>
  );
}
