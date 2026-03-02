"use client";

import * as React from "react";

import { apiJson, PromptTemplateOut } from "@/app/lib/fce";

function fmt(dt: string) {
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return dt;
  }
}

export default function PromptTemplatesPage() {
  const [items, setItems] = React.useState<PromptTemplateOut[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const [name, setName] = React.useState("Momentum v1");
  const [system, setSystem] = React.useState(
    "You are a trading decision engine. Output ONLY strict JSON with schema_version=1.",
  );
  const [user, setUser] = React.useState(
    "market_id={{market_id}}\n" +
      "tick_time={{tick_time}}\n" +
      "risk={{risk_style}}\n\n" +
      "Recent closes:\n" +
      "{{#closes}}- {{.}}\n{{/closes}}\n\n" +
      "Return JSON like {\"schema_version\":1,\"targets\":{\"{{market_id}}\":0.25}}",
  );
  const [varsSchema, setVarsSchema] = React.useState(
    JSON.stringify(
      {
        risk_style: {
          type: "string",
          enum: ["conservative", "balanced", "aggressive"],
        },
      },
      null,
      2,
    ),
  );

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiJson<PromptTemplateOut[]>("/prompt_templates");
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

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    let vars_schema: Record<string, unknown> | null = null;
    try {
      vars_schema = varsSchema.trim() ? (JSON.parse(varsSchema) as Record<string, unknown>) : null;
    } catch {
      setError("vars_schema must be valid JSON (or empty)");
      return;
    }

    setLoading(true);
    try {
      await apiJson<PromptTemplateOut>("/prompt_templates", {
        method: "POST",
        body: {
          name,
          engine: "mustache",
          system_template: system,
          user_template: user,
          vars_schema,
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
          <h2 className="font-display text-3xl tracking-tight">Prompt Templates</h2>
          <p className="mt-1 text-sm leading-6 text-black/60">
            Stored in the backend and snapshotted into runs. Use variables like{" "}
            <span className="font-mono">{"{{risk_style}}"}</span>.
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
        <h3 className="font-display text-xl tracking-tight">Create Template</h3>
        <form onSubmit={onCreate} className="mt-4 grid gap-4">
          <label className="grid gap-1 text-sm">
            <span className="text-black/65">Name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-10 rounded-xl border border-black/15 bg-white/70 px-3"
              required
            />
          </label>

          <label className="grid gap-1 text-sm">
            <span className="text-black/65">System Template</span>
            <textarea
              value={system}
              onChange={(e) => setSystem(e.target.value)}
              rows={3}
              className="rounded-2xl border border-black/15 bg-white/70 p-3 font-mono text-xs"
              required
            />
          </label>

          <label className="grid gap-1 text-sm">
            <span className="text-black/65">User Template</span>
            <textarea
              value={user}
              onChange={(e) => setUser(e.target.value)}
              rows={8}
              className="rounded-2xl border border-black/15 bg-white/70 p-3 font-mono text-xs"
              required
            />
          </label>

          <label className="grid gap-1 text-sm">
            <span className="text-black/65">Vars Schema (JSON, optional)</span>
            <textarea
              value={varsSchema}
              onChange={(e) => setVarsSchema(e.target.value)}
              rows={6}
              className="rounded-2xl border border-black/15 bg-white/70 p-3 font-mono text-xs"
            />
          </label>

          <div className="flex items-center justify-end gap-3">
            <button
              type="submit"
              className="rounded-full bg-[color:var(--ink)] px-5 py-2.5 text-sm font-medium text-[color:var(--surface)] hover:bg-black"
            >
              Create
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
          <h3 className="font-display text-xl tracking-tight">Templates</h3>
          <div className="text-xs text-black/55">{items.length} total</div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-black/50">
              <tr>
                <th className="px-6 py-3">ID</th>
                <th className="px-6 py-3">Name</th>
                <th className="px-6 py-3">Engine</th>
                <th className="px-6 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-black/5">
              {items.map((t) => (
                <tr key={t.template_id} className="hover:bg-black/[0.02]">
                  <td className="px-6 py-3 font-mono text-xs text-black/70">
                    {t.template_id}
                  </td>
                  <td className="px-6 py-3">{t.name}</td>
                  <td className="px-6 py-3">{t.engine}</td>
                  <td className="px-6 py-3 text-xs text-black/60">
                    {fmt(t.created_at)}
                  </td>
                </tr>
              ))}
              {items.length === 0 ? (
                <tr>
                  <td className="px-6 py-10 text-sm text-black/55" colSpan={4}>
                    No templates yet.
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
