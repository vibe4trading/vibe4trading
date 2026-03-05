"use client";

import * as React from "react";

import {
  apiJson,
  MeOut,
  ModelAdminCreateRequest,
  ModelAdminOut,
  ModelAdminUpdateRequest,
} from "@/app/lib/v4t";

export default function AdminModelsPage() {
  const [me, setMe] = React.useState<MeOut | null>(null);
  const [models, setModels] = React.useState<ModelAdminOut[]>([]);
  const [drafts, setDrafts] = React.useState<Record<string, ModelAdminUpdateRequest>>({});

  const [create, setCreate] = React.useState<ModelAdminCreateRequest>({
    model_key: "",
    label: "",
    api_base_url: "",
    enabled: true,
  });

  const [loading, setLoading] = React.useState(false);
  const [savingKey, setSavingKey] = React.useState<string | null>(null);
  const [deletingKey, setDeletingKey] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await apiJson<ModelAdminOut[]>("/admin/models");
      setModels(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    apiJson<MeOut>("/me")
      .then((data) => setMe(data))
      .catch(() => setMe(null));
  }, []);

  React.useEffect(() => {
    if (me?.is_admin) refresh();
  }, [me, refresh]);

  const isAdmin = Boolean(me?.is_admin);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const key = (create.model_key || "").trim();
    if (!key) {
      setError("model_key is required");
      return;
    }

    setLoading(true);
    try {
      await apiJson<ModelAdminOut>("/admin/models", {
        method: "POST",
        body: {
          model_key: key,
          label: create.label || null,
          api_base_url: create.api_base_url || null,
          enabled: create.enabled ?? true,
        },
      });
      setCreate({ model_key: "", label: "", api_base_url: "", enabled: true });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onSave(modelKey: string) {
    setError(null);
    setSavingKey(modelKey);
    try {
      const base = models.find((m) => m.model_key === modelKey);
      if (!base) return;
      const draft = drafts[modelKey] ?? {};

      const body: ModelAdminUpdateRequest = {
        label: draft.label ?? base.label,
        api_base_url: draft.api_base_url ?? base.api_base_url,
        enabled: draft.enabled ?? base.enabled,
      };

      await apiJson<ModelAdminOut>(`/admin/models/${encodeURIComponent(modelKey)}`, {
        method: "PUT",
        body,
      });
      setDrafts((prev) => {
        const next = { ...prev };
        delete next[modelKey];
        return next;
      });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSavingKey(null);
    }
  }

  async function onDelete(modelKey: string) {
    setError(null);
    setDeletingKey(modelKey);
    try {
      await apiJson<{ deleted: boolean }>(`/admin/models/${encodeURIComponent(modelKey)}`, {
        method: "DELETE",
      });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeletingKey(null);
    }
  }

  if (me && !isAdmin) {
    return (
      <div className="animate-rise flex flex-col gap-4">
        <h2 className="font-display text-3xl tracking-tight text-white">Model Management</h2>
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm font-medium text-rose-200">
          Admin access required.
        </div>
      </div>
    );
  }

  return (
    <div className="animate-rise flex flex-col gap-8">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold tracking-widest text-[color:var(--accent-2)]">
            ADMIN • MODEL REGISTRY
          </p>
          <h2 className="mt-2 font-display text-4xl tracking-tight text-white drop-shadow-sm">Models</h2>
          <p className="mt-2 text-sm leading-relaxed text-zinc-400">
            Define the predefined models list and the API base URL used for each model.
          </p>
        </div>

        <button
          type="button"
          onClick={refresh}
          className="rounded-full border border-white/20 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-white/10 hover:border-white/30 hover:shadow-[0_0_15px_rgba(255,255,255,0.1)]"
          disabled={!isAdmin || loading}
        >
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm font-medium text-rose-200 shadow-[0_0_20px_rgba(244,63,94,0.1)]">
          {error}
        </div>
      ) : null}

      <section className="animate-rise-1 rounded-3xl border border-[color:var(--border)] bg-white/5 p-6 shadow-lg backdrop-blur-md">
        <h3 className="font-display text-xl tracking-tight text-white mb-6">Add Model</h3>
        <form onSubmit={onCreate} className="grid gap-5 md:grid-cols-2">
          <label className="grid gap-1.5 text-sm">
            <span className="text-zinc-400 font-medium">model_key</span>
            <input
              value={create.model_key}
              onChange={(e) => setCreate((p) => ({ ...p, model_key: e.target.value }))}
              className="h-11 rounded-xl border border-white/10 bg-black/40 px-4 font-mono text-sm text-white placeholder-zinc-600 focus:border-[color:var(--accent-2)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent-2)] transition-all"
              placeholder="gpt-4o-mini"
              required
            />
          </label>
          <label className="grid gap-1.5 text-sm">
            <span className="text-zinc-400 font-medium">label</span>
            <input
              value={create.label ?? ""}
              onChange={(e) => setCreate((p) => ({ ...p, label: e.target.value }))}
              className="h-11 rounded-xl border border-white/10 bg-black/40 px-4 text-sm text-white placeholder-zinc-600 focus:border-[color:var(--accent-2)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent-2)] transition-all"
              placeholder="GPT-4o mini"
            />
          </label>
          <label className="grid gap-1.5 text-sm md:col-span-2">
            <span className="text-zinc-400 font-medium">api_base_url</span>
            <input
              value={create.api_base_url ?? ""}
              onChange={(e) => setCreate((p) => ({ ...p, api_base_url: e.target.value }))}
              className="h-11 rounded-xl border border-white/10 bg-black/40 px-4 font-mono text-xs text-white placeholder-zinc-600 focus:border-[color:var(--accent-2)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent-2)] transition-all"
              placeholder="https://openrouter.ai/api/v1"
            />
          </label>
          <label className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/40 px-4 py-2 cursor-pointer transition-all hover:bg-white/5 md:col-span-2">
            <input
              type="checkbox"
              checked={Boolean(create.enabled)}
              onChange={(e) => setCreate((p) => ({ ...p, enabled: e.target.checked }))}
              className="h-4 w-4 accent-[color:var(--accent-2)]"
            />
            <span className="text-sm text-zinc-200">enabled</span>
          </label>
          <div className="md:col-span-2 flex items-center justify-end pt-2">
            <button
              type="submit"
              className="rounded-full bg-white px-8 py-3 text-sm font-bold text-black transition-all hover:bg-zinc-200 hover:shadow-[0_0_20px_rgba(255,255,255,0.2)] disabled:opacity-50"
              disabled={loading}
            >
              Add
            </button>
          </div>
        </form>
      </section>

      <section className="animate-rise-2 rounded-3xl border border-[color:var(--border)] bg-white/5 p-6 shadow-lg backdrop-blur-md">
        <h3 className="font-display text-xl tracking-tight text-white mb-6">Models</h3>
        <div className="grid gap-3">
          {models.length === 0 ? (
            <div className="text-sm text-zinc-400">No models defined yet.</div>
          ) : null}
          {models.map((m) => {
            const d = drafts[m.model_key] ?? {};
            const label = d.label ?? m.label ?? "";
            const apiBaseUrl = d.api_base_url ?? m.api_base_url ?? "";
            const enabled = d.enabled ?? m.enabled;
            return (
              <div
                key={m.model_key}
                className="rounded-2xl border border-white/10 bg-black/30 p-4"
              >
                <div className="grid gap-4 md:grid-cols-12 md:items-end">
                  <div className="md:col-span-3">
                    <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">model_key</div>
                    <div className="mt-1 font-mono text-sm text-white">{m.model_key}</div>
                  </div>
                  <label className="md:col-span-3 grid gap-1.5 text-sm">
                    <span className="text-zinc-400 font-medium">label</span>
                    <input
                      value={label}
                      onChange={(e) =>
                        setDrafts((p) => ({
                          ...p,
                          [m.model_key]: { ...p[m.model_key], label: e.target.value },
                        }))
                      }
                      className="h-10 rounded-xl border border-white/10 bg-black/40 px-3 text-sm text-white focus:border-[color:var(--accent-2)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent-2)] transition-all"
                    />
                  </label>
                  <label className="md:col-span-4 grid gap-1.5 text-sm">
                    <span className="text-zinc-400 font-medium">api_base_url</span>
                    <input
                      value={apiBaseUrl}
                      onChange={(e) =>
                        setDrafts((p) => ({
                          ...p,
                          [m.model_key]: { ...p[m.model_key], api_base_url: e.target.value },
                        }))
                      }
                      className="h-10 rounded-xl border border-white/10 bg-black/40 px-3 font-mono text-xs text-white focus:border-[color:var(--accent-2)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent-2)] transition-all"
                    />
                  </label>
                  <label className="md:col-span-1 flex items-center gap-2 rounded-xl border border-white/10 bg-black/40 px-3 py-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={Boolean(enabled)}
                      onChange={(e) =>
                        setDrafts((p) => ({
                          ...p,
                          [m.model_key]: { ...p[m.model_key], enabled: e.target.checked },
                        }))
                      }
                      className="h-4 w-4 accent-[color:var(--accent-2)]"
                    />
                    <span className="text-xs text-zinc-200">on</span>
                  </label>
                  <div className="md:col-span-1 flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => onSave(m.model_key)}
                      className="rounded-full border border-white/20 bg-white/5 px-4 py-2 text-xs font-semibold text-white transition-all hover:bg-white/10 disabled:opacity-50"
                      disabled={savingKey === m.model_key}
                    >
                      {savingKey === m.model_key ? "Saving…" : "Save"}
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(m.model_key)}
                      className="rounded-full border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-xs font-semibold text-rose-300 transition-all hover:bg-rose-500/20 disabled:opacity-50"
                      disabled={deletingKey === m.model_key}
                    >
                      {deletingKey === m.model_key ? "Deleting…" : "Delete"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
