import * as React from "react";

import { useParams } from "react-router-dom";

import { LineChart } from "@/app/components/LineChart";
import { SEO } from "@/app/components/SEO";
import {
  apiJson,
  getApiBaseUrl,
  LlmDecision,
  PricePoint,
  RunConfigSnapshot,
  RunOut,
  TimelinePoint,
} from "@/app/lib/v4t";

type ChartPoint = { xLabel: string; y: number };

function fmt(iso: string | null) {
  if (!iso) return "–";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function timeLabel(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function decisionTarget(dec: LlmDecision) {
  const v = dec.targets?.[dec.market_id];
  if (v !== undefined) return v;
  const firstKey = dec.targets ? Object.keys(dec.targets)[0] : undefined;
  return firstKey ? dec.targets[firstKey] : "";
}

function findLastIndexAtOrBefore(sortedMs: number[], targetMs: number) {
  let lo = 0;
  let hi = sortedMs.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const v = sortedMs[mid];
    if (v <= targetMs) {
      ans = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return ans;
}

type StreamEvent = {
  event_type: string;
  observed_at: string;
  payload: Record<string, unknown>;
};

export default function RunWatchPage() {
  const runId = useParams<{ runId: string }>().runId ?? "";

  const [run, setRun] = React.useState<RunOut | null>(null);
  const [cfg, setCfg] = React.useState<RunConfigSnapshot | null>(null);

  const [pricesAll, setPricesAll] = React.useState<PricePoint[]>([]);
  const [pricePoints, setPricePoints] = React.useState<ChartPoint[]>([]);

  const [equityPoints, setEquityPoints] = React.useState<ChartPoint[]>([]);
  const [decisions, setDecisions] = React.useState<LlmDecision[]>([]);

  const [error, setError] = React.useState<string | null>(null);

  const [activeTick, setActiveTick] = React.useState<string | null>(null);
  const [streamText, setStreamText] = React.useState<string>("");
  const [streamHistory, setStreamHistory] = React.useState<
    { tick_time: string; text: string; decision?: LlmDecision }[]
  >([]);

  const baseIntervalSeconds = cfg?.scheduler?.base_interval_seconds ?? 14400;
  const wallSecondsPerTick = cfg?.replay?.pace_seconds_per_base_tick ?? 2;

  const pricesMs = React.useMemo(() => {
    return pricesAll.map((p) => new Date(p.observed_at).getTime());
  }, [pricesAll]);

  const priceMarkers = React.useMemo(() => {
    const out: { index: number; color?: string; label?: string }[] = [];
    for (const d of decisions) {
      const t = new Date(d.tick_time).getTime();
      const idx = findLastIndexAtOrBefore(pricesMs, t);
      if (idx >= 0 && idx < pricePoints.length) {
        out.push({
          index: idx,
          color: d.accepted ? "rgba(34,197,94,0.55)" : "rgba(244,63,94,0.55)",
          label: d.accepted ? "A" : "R",
        });
      }
    }
    return out;
  }, [decisions, pricePoints.length, pricesMs]);

  const equityMarkers = React.useMemo(() => {
    const out: { index: number; color?: string; label?: string }[] = [];
    for (const d of decisions) {
      const label = timeLabel(d.tick_time);
      const idx = equityPoints.findIndex((p) => p.xLabel === label);
      if (idx >= 0) {
        out.push({
          index: idx,
          color: d.accepted ? "rgba(34,197,94,0.55)" : "rgba(244,63,94,0.55)",
          label: d.accepted ? "A" : "R",
        });
      }
    }
    return out;
  }, [decisions, equityPoints]);

  const playbackRef = React.useRef<{
    running: boolean;
    startWallMs: number;
    fromSimMs: number;
    toSimMs: number;
    raf: number | null;
    nextPriceIndex: number;
  }>({
    running: false,
    startWallMs: 0,
    fromSimMs: 0,
    toSimMs: 0,
    raf: null,
    nextPriceIndex: 0,
  });

  const activeTickRef = React.useRef<string | null>(null);
  const streamTextRef = React.useRef<string>("");
  const equityPointsRef = React.useRef<ChartPoint[]>([]);
  const portfolioRafRef = React.useRef<number | null>(null);

  const refresh = React.useCallback(async () => {
    try {
      const [runRes, cfgRes, pricesRes, tlRes, decRes] = await Promise.all([
        apiJson<RunOut>(`/runs/${runId}`),
        apiJson<RunConfigSnapshot>(`/runs/${runId}/config`),
        apiJson<PricePoint[]>(`/runs/${runId}/prices?limit=5000`),
        apiJson<TimelinePoint[]>(`/runs/${runId}/timeline`),
        apiJson<LlmDecision[]>(`/runs/${runId}/decisions?limit=500&offset=0`),
      ]);

      setRun(runRes);
      setCfg(cfgRes);
      setPricesAll(pricesRes);

      setEquityPoints(
        tlRes.map((p) => ({ xLabel: timeLabel(p.observed_at), y: p.equity_quote })),
      );
      setDecisions(decRes);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load run data");
    }
  }, [runId]);

  React.useEffect(() => {
    refresh().catch(() => null);
  }, [refresh]);

  React.useEffect(() => {
    activeTickRef.current = activeTick;
  }, [activeTick]);

  React.useEffect(() => {
    streamTextRef.current = streamText;
  }, [streamText]);

  React.useEffect(() => {
    equityPointsRef.current = equityPoints;
  }, [equityPoints]);

  React.useEffect(() => {
    if (pricesAll.length === 0) return;
    playbackRef.current.nextPriceIndex = 0;
    setPricePoints([]);
  }, [pricesAll]);

  const startPlayback = React.useCallback(
    (fromTickIso: string) => {
      if (pricesAll.length === 0) return;
      const fromSim = new Date(fromTickIso).getTime();
      const toSim = fromSim + baseIntervalSeconds * 1000;

      playbackRef.current.running = true;
      playbackRef.current.startWallMs = performance.now();
      playbackRef.current.fromSimMs = fromSim;
      playbackRef.current.toSimMs = toSim;

      const step = () => {
        if (!playbackRef.current.running) return;
        const nowWall = performance.now();
        const t = Math.max(
          0,
          Math.min(1, (nowWall - playbackRef.current.startWallMs) / (wallSecondsPerTick * 1000)),
        );
        const playhead = playbackRef.current.fromSimMs +
          (playbackRef.current.toSimMs - playbackRef.current.fromSimMs) * t;

        let i = playbackRef.current.nextPriceIndex;
        while (i < pricesAll.length) {
          const ts = new Date(pricesAll[i].observed_at).getTime();
          if (ts > playhead) break;
          i += 1;
        }

        if (i !== playbackRef.current.nextPriceIndex) {
          playbackRef.current.nextPriceIndex = i;
          const nextPoints: ChartPoint[] = [];
          for (let j = 0; j < i; j += 1) {
            const p = pricesAll[j];
            nextPoints.push({ xLabel: timeLabel(p.observed_at), y: p.price });
          }
          setPricePoints(nextPoints);
        }

        if (t >= 1) {
          playbackRef.current.running = false;
          playbackRef.current.raf = null;
          return;
        }
        playbackRef.current.raf = requestAnimationFrame(step);
      };

      if (playbackRef.current.raf != null) {
        cancelAnimationFrame(playbackRef.current.raf);
      }
      playbackRef.current.raf = requestAnimationFrame(step);
    },
    [baseIntervalSeconds, pricesAll, wallSecondsPerTick],
  );

  const stopPlayback = React.useCallback(() => {
    playbackRef.current.running = false;
    if (playbackRef.current.raf != null) {
      cancelAnimationFrame(playbackRef.current.raf);
      playbackRef.current.raf = null;
    }
  }, []);

  const startPlaybackRef = React.useRef(startPlayback);
  React.useEffect(() => {
    startPlaybackRef.current = startPlayback;
  }, [startPlayback]);

  const stopPlaybackRef = React.useRef(stopPlayback);
  React.useEffect(() => {
    stopPlaybackRef.current = stopPlayback;
  }, [stopPlayback]);

  React.useEffect(() => {
    const es = new EventSource(`${getApiBaseUrl()}/runs/${runId}/stream`);

    const onLlmStart = (e: MessageEvent<string>) => {
      try {
        stopPlaybackRef.current();
        const ev = JSON.parse(e.data) as StreamEvent;
        const tickTime = String(ev.payload.tick_time ?? "");
        if (tickTime) {
          setActiveTick(tickTime);
          setStreamText("");
        }
      } catch (err) {
        console.error("[watch] Failed to parse llm_start event:", err);
      }
    };

    const onLlmDelta = (e: MessageEvent<string>) => {
      try {
        const ev = JSON.parse(e.data) as StreamEvent;
        const delta = ev.payload.delta;
        if (typeof delta === "string" && delta) {
          setStreamText((prev) => prev + delta);
        }
      } catch (err) {
        console.error("[watch] Failed to parse llm_delta event:", err);
      }
    };

    const onDecision = (e: MessageEvent<string>) => {
      try {
        const ev = JSON.parse(e.data) as StreamEvent;
        const raw = ev.payload;
        if (typeof raw !== "object" || raw === null || !("tick_time" in raw)) return;
        const payload = raw as LlmDecision;
        setDecisions((prev) => {
          const byTick = new Map<string, LlmDecision>();
          for (const d of prev) byTick.set(d.tick_time, d);
          byTick.set(payload.tick_time, payload);
          const merged = Array.from(byTick.values());
          merged.sort((a, b) => a.tick_time.localeCompare(b.tick_time));
          return merged;
        });

        if (payload.tick_time) {
          setStreamHistory((prev) => {
            const tick = payload.tick_time;
            const existing = prev.find((x) => x.tick_time === tick);
            const item = {
              tick_time: tick,
              text: activeTickRef.current === tick ? streamTextRef.current : (existing?.text ?? ""),
              decision: payload,
            };
            const others = prev.filter((x) => x.tick_time !== tick);
            return [...others, item].sort((a, b) => a.tick_time.localeCompare(b.tick_time));
          });
          startPlaybackRef.current(payload.tick_time);
        }
      } catch (err) {
        console.error("[watch] Failed to parse decision event:", err);
      }
    };

    const onPortfolio = (e: MessageEvent<string>) => {
      try {
        const ev = JSON.parse(e.data) as StreamEvent;
        const snapTime = String(ev.payload.snapshot_time ?? "");
        const eq = ev.payload.equity_quote;
        if (!snapTime || typeof eq !== "string") return;
        const target = Number(eq);
        if (!isFinite(target)) return;

        const label = timeLabel(snapTime);
        const from = equityPointsRef.current[equityPointsRef.current.length - 1]?.y ?? target;
        setEquityPoints((prev) => {
          const next = [...prev, { xLabel: label, y: from }];
          equityPointsRef.current = next;
          return next;
        });

        const start = performance.now();
        const dur = 450;
        const animate = () => {
          const t = Math.min(1, (performance.now() - start) / dur);
          const y = from + (target - from) * t;

          const current = equityPointsRef.current;
          if (current.length === 0) return;
          const idx = current.length - 1;
          const next = current.slice();
          next[idx] = { ...next[idx], y };
          equityPointsRef.current = next;
          setEquityPoints(next);

          if (t < 1) {
            portfolioRafRef.current = requestAnimationFrame(animate);
          } else {
            portfolioRafRef.current = null;
          }
        };
        if (portfolioRafRef.current != null) {
          cancelAnimationFrame(portfolioRafRef.current);
        }
        portfolioRafRef.current = requestAnimationFrame(animate);
      } catch (err) {
        console.error("[watch] Failed to parse portfolio event:", err);
      }
    };

    es.addEventListener("llm_start", onLlmStart as EventListener);
    es.addEventListener("llm_delta", onLlmDelta as EventListener);
    es.addEventListener("llm.decision", onDecision as EventListener);
    es.addEventListener("portfolio", onPortfolio as EventListener);

    es.onerror = () => {
      console.warn("[v4t] EventSource error — browser will auto-reconnect");
    };

    return () => {
      es.close();
      stopPlaybackRef.current();
      if (portfolioRafRef.current != null) {
        cancelAnimationFrame(portfolioRafRef.current);
        portfolioRafRef.current = null;
      }
    };
  }, [runId]);

  return (
    <div className="animate-rise flex flex-col gap-6">
      <SEO title="Watch Run" description="Live run progress." noindex />
      {error ? (
        <div className="flex items-center justify-between gap-4 rounded-2xl border border-red-500/30 bg-red-500/10 px-5 py-4 text-sm text-red-300">
          <span>{error}</span>
          <button
            type="button"
            onClick={() => { setError(null); refresh().catch(() => null); }}
            className="shrink-0 rounded-lg border border-red-500/40 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-red-200 transition-colors hover:bg-red-500/20"
          >
            Retry
          </button>
        </div>
      ) : null}
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold tracking-widest text-[color:var(--accent-2)]">
            RUN WATCH
          </p>
          <h2 className="mt-2 font-display text-4xl tracking-tight text-white drop-shadow-sm">
            Dynamic View
          </h2>
          <div className="mt-3 grid gap-4 text-sm text-zinc-400 md:grid-cols-3">
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">run_id</span>
              <span className="font-mono text-white/90">{runId}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">status</span>
              <span className="font-mono text-white/90">{run?.status ?? "…"}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">tick_time</span>
              <span className="font-mono text-white/90">{fmt(activeTick)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 flex flex-col gap-4">
          <LineChart
            points={pricePoints}
            title="Market Price"
            strokeFrom="rgba(56,189,248,0.95)"
            strokeTo="rgba(34,197,94,0.85)"
            markers={priceMarkers}
          />
          <LineChart
            points={equityPoints}
            title="PnL / Equity"
            strokeFrom="rgba(20,184,166,0.95)"
            strokeTo="rgba(249,115,22,0.85)"
            markers={equityMarkers}
          />
        </div>

        <div className="rounded-3xl border border-[color:var(--border)] bg-white/5 shadow-lg backdrop-blur-md overflow-hidden">
          <div className="border-b border-white/10 bg-white/5 px-5 py-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">LLM Stream</div>
            <div className="mt-1 text-sm text-zinc-300">
              {cfg?.mode === "replay" ? "Replay" : "Live"} • {wallSecondsPerTick}s per tick
            </div>
          </div>

          <div className="p-5">
            <div className="rounded-2xl border border-white/10 bg-black/30 p-4 font-mono text-xs leading-relaxed text-zinc-200 whitespace-pre-wrap min-h-[220px]">
              {streamText || "(waiting for next tick…)"}
            </div>

            <div className="mt-5">
              <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Decisions</div>
              <div className="mt-3 grid gap-3">
                {streamHistory
                  .slice()
                  .reverse()
                  .slice(0, 8)
                  .map((h) => (
                    <div
                      key={h.tick_time}
                      className="rounded-2xl border border-white/10 bg-black/20 p-4"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="font-mono text-[0.7rem] text-zinc-400">{fmt(h.tick_time)}</div>
                        {h.decision ? (
                          <span
                            className={
                              h.decision.accepted
                                ? "inline-flex items-center rounded-full bg-[color:var(--accent)]/10 border border-[color:var(--accent)]/30 px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wider text-[color:var(--accent)]"
                                : "inline-flex items-center rounded-full bg-rose-500/10 border border-rose-500/30 px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wider text-rose-400"
                            }
                          >
                            {h.decision.accepted ? "accepted" : "rejected"}
                          </span>
                        ) : null}
                      </div>
                      {h.decision ? (
                        <div className="mt-2 text-xs text-zinc-300">
                          target: <span className="font-mono text-white">{String(decisionTarget(h.decision))}</span>
                        </div>
                      ) : null}
                      <div className="mt-3 font-mono text-[0.7rem] text-zinc-400 whitespace-pre-wrap line-clamp-5 hover:line-clamp-none transition-all">
                        {h.text || "(no stream captured)"}
                      </div>
                    </div>
                  ))}
                {streamHistory.length === 0 ? (
                  <div className="text-sm text-zinc-500">No decisions yet.</div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
