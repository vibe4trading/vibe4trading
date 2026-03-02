"use client";

import * as React from "react";

import {
  apiJson,
  DatasetCategory,
  DatasetOut,
  DatasetSource,
  isoFromLocalInput,
} from "@/app/lib/fce";

function defaultParams(category: DatasetCategory, source: DatasetSource) {
  if (category === "spot" && source === "demo") {
    return { market_id: "spot:demo:DEMO", base_price: 1.0 };
  }
  if (category === "spot" && source === "dexscreener") {
    return { chain_id: "solana", pair_id: "<pairAddress>" };
  }
  if (category === "sentiment" && source === "demo") {
    return { market_id: "spot:demo:DEMO" };
  }
  if (category === "sentiment" && source === "rss") {
    return {
      // You can also set feeds via FCE_SENTIMENT_RSS_FEEDS on the backend.
      feeds: ["https://news.google.com/rss/search?q=solana+token&hl=en-US&gl=US&ceid=US:en"],
      max_items: 30,
      model_key: "stub",
    };
  }
  return {};
}

function fmt(dt: string) {
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return dt;
  }
}

function badgeClass(status: string) {
  if (status === "ready") return "bg-emerald-100 text-emerald-900";
  if (status === "running") return "bg-amber-100 text-amber-900";
  if (status === "failed") return "bg-rose-100 text-rose-900";
  return "bg-zinc-200 text-zinc-900";
}

export default function DatasetsPage() {
  const [items, setItems] = React.useState<DatasetOut[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const [category, setCategory] = React.useState<DatasetCategory>("spot");
  const [source, setSource] = React.useState<DatasetSource>("demo");
  const [startLocal, setStartLocal] = React.useState(() => {
    const d = new Date(Date.now() - 6 * 3600 * 1000);
    return d.toISOString().slice(0, 16);
  });
  const [endLocal, setEndLocal] = React.useState(() => {
    const d = new Date();
    return d.toISOString().slice(0, 16);
  });
  const [paramsText, setParamsText] = React.useState(() =>
    JSON.stringify(defaultParams("spot", "demo"), null, 2),
  );

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiJson<DatasetOut[]>("/datasets");
      setItems(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  React.useEffect(() => {
    setParamsText(JSON.stringify(defaultParams(category, source), null, 2));
  }, [category, source]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    let params: Record<string, unknown>;
    try {
      params = paramsText.trim() ? (JSON.parse(paramsText) as Record<string, unknown>) : {};
    } catch {
      setError("params must be valid JSON");
      return;
    }

    setLoading(true);
    try {
      await apiJson<DatasetOut>("/datasets", {
        method: "POST",
        body: {
          category,
          source,
          start: isoFromLocalInput(startLocal),
          end: isoFromLocalInput(endLocal),
          params,
        },
      });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-3xl tracking-tight">Datasets</h2>
          <p className="mt-1 text-sm leading-6 text-black/60">
            Import windows into canonical events. Source <span className="font-mono">demo</span> is
            deterministic; <span className="font-mono">dexscreener</span> is a seeded synthetic backfill;
            <span className="font-mono"> empty</span> sentiment is allowed.
          </p>
        </div>

        <button
          type="button"
          onClick={refresh}
          className="rounded-full border border-black/15 bg-white/60 px-4 py-2 text-sm font-medium text-black/80 hover:bg-white"
        >
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      <section className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-6 shadow-[var(--shadow)]">
        <h3 className="font-display text-xl tracking-tight">Create Dataset</h3>
        <form onSubmit={onCreate} className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="grid gap-1 text-sm">
            <span className="text-black/65">Category</span>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as DatasetCategory)}
              className="h-10 rounded-xl border border-black/15 bg-white/70 px-3"
            >
              <option value="spot">spot</option>
              <option value="sentiment">sentiment</option>
            </select>
          </label>

          <label className="grid gap-1 text-sm">
            <span className="text-black/65">Source</span>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value as DatasetSource)}
              className="h-10 rounded-xl border border-black/15 bg-white/70 px-3"
            >
              {category === "spot" ? (
                <>
                  <option value="demo">demo</option>
                  <option value="dexscreener">dexscreener</option>
                </>
              ) : (
                <>
                  <option value="demo">demo</option>
                  <option value="rss">rss</option>
                  <option value="empty">empty</option>
                </>
              )}
            </select>
          </label>

          <label className="grid gap-1 text-sm">
            <span className="text-black/65">Start</span>
            <input
              type="datetime-local"
              value={startLocal}
              onChange={(e) => setStartLocal(e.target.value)}
              className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              required
            />
          </label>

          <label className="grid gap-1 text-sm">
            <span className="text-black/65">End</span>
            <input
              type="datetime-local"
              value={endLocal}
              onChange={(e) => setEndLocal(e.target.value)}
              className="h-10 rounded-xl border border-black/15 bg-white/70 px-3 font-mono text-xs"
              required
            />
          </label>

          <label className="md:col-span-2 grid gap-1 text-sm">
            <span className="text-black/65">Params (JSON)</span>
            <textarea
              value={paramsText}
              onChange={(e) => setParamsText(e.target.value)}
              rows={8}
              className="rounded-2xl border border-black/15 bg-white/70 p-3 font-mono text-xs"
            />
          </label>

          <div className="md:col-span-2 flex items-center justify-between gap-3">
            <div className="text-xs text-black/55">
              Tip: For DexScreener, set <span className="font-mono">chain_id</span> +
              <span className="font-mono"> pair_id</span> (pair address).
            </div>
            <button
              type="submit"
              className="rounded-full bg-[color:var(--ink)] px-5 py-2.5 text-sm font-medium text-[color:var(--surface)] hover:bg-black"
            >
              Create + Enqueue Import
            </button>
          </div>
        </form>

        {error ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900">
            {error}
          </div>
        ) : null}
      </section>

      <section className="overflow-hidden rounded-3xl border border-black/10 bg-white/60 shadow-[var(--shadow)]">
        <div className="flex items-center justify-between border-b border-black/10 px-6 py-4">
          <h3 className="font-display text-xl tracking-tight">Recent</h3>
          <div className="text-xs text-black/55">{items.length} total</div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-black/50">
              <tr>
                <th className="px-6 py-3">ID</th>
                <th className="px-6 py-3">Category</th>
                <th className="px-6 py-3">Source</th>
                <th className="px-6 py-3">Window</th>
                <th className="px-6 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-black/5">
              {items.map((d) => (
                <tr key={d.dataset_id} className="hover:bg-black/[0.02]">
                  <td className="px-6 py-3 font-mono text-xs text-black/70">
                    {d.dataset_id}
                  </td>
                  <td className="px-6 py-3">{d.category}</td>
                  <td className="px-6 py-3">{d.source}</td>
                  <td className="px-6 py-3 text-xs text-black/60">
                    {fmt(d.start)} → {fmt(d.end)}
                  </td>
                  <td className="px-6 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${badgeClass(d.status)}`}>
                      {d.status}
                    </span>
                    {d.error ? (
                      <div className="mt-1 text-xs text-rose-800">{d.error}</div>
                    ) : null}
                  </td>
                </tr>
              ))}
              {items.length === 0 ? (
                <tr>
                  <td className="px-6 py-10 text-sm text-black/55" colSpan={5}>
                    No datasets yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
