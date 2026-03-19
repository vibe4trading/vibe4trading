import * as React from "react";
import { useTranslation } from "react-i18next";

import { SEO } from "@/app/components/SEO";
import {
  AdminModelAccessIndexOut,
  AdminModelAccessUpdateRequest,
  AdminModelAccessUserOut,
  apiJson,
  MeOut,
  ModelAdminCreateRequest,
  ModelAdminOut,
  ModelAdminUpdateRequest,
} from "@/app/lib/v4t";

const USER_PAGE_SIZE = 100;

export default function AdminModelsPage() {
  const { t } = useTranslation("admin");
  const [me, setMe] = React.useState<MeOut | null>(null);
  const [models, setModels] = React.useState<ModelAdminOut[]>([]);
  const [modelAccess, setModelAccess] = React.useState<AdminModelAccessIndexOut | null>(null);
  const [drafts, setDrafts] = React.useState<Record<string, ModelAdminUpdateRequest>>({});
  const [userAccessDrafts, setUserAccessDrafts] = React.useState<Record<string, string>>({});

  const [create, setCreate] = React.useState<ModelAdminCreateRequest>({
    model_key: "",
    label: "",
    api_base_url: "",
    api_key: "",
    enabled: true,
  });

  const [loading, setLoading] = React.useState(false);
  const [savingKey, setSavingKey] = React.useState<string | null>(null);
  const [deletingKey, setDeletingKey] = React.useState<string | null>(null);
  const [savingUserId, setSavingUserId] = React.useState<string | null>(null);
  const [userOffset, setUserOffset] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async (nextOffset = 0) => {
    setLoading(true);
    setError(null);
    try {
      const [rows, access] = await Promise.all([
        apiJson<ModelAdminOut[]>("/admin/models"),
        apiJson<AdminModelAccessIndexOut>(
          `/admin/model-access?limit=${USER_PAGE_SIZE}&offset=${nextOffset}`,
        ),
      ]);
      setModels(rows);
      setModelAccess(access);
      setUserOffset(nextOffset);
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
    if (me?.is_admin) refresh(0);
  }, [me, refresh]);

  const isAdmin = Boolean(me?.is_admin);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const key = (create.model_key || "").trim();
    const apiKey = (create.api_key || "").trim();
    if (!key) {
      setError(t("errors.modelKeyRequired"));
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
          api_key: apiKey || null,
          enabled: create.enabled ?? true,
        },
      });
      setCreate({ model_key: "", label: "", api_base_url: "", api_key: "", enabled: true });
      await refresh(userOffset);
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
      const apiKey = (draft.api_key || "").trim();
      const clearApiKey = Boolean(draft.clear_api_key);

      if (clearApiKey && apiKey) {
        setError(t("errors.apiKeyConflict"));
        return;
      }

      const body: ModelAdminUpdateRequest = {
        label: draft.label ?? base.label,
        api_base_url: draft.api_base_url ?? base.api_base_url,
        enabled: draft.enabled ?? base.enabled,
        ...(apiKey ? { api_key: apiKey } : {}),
        ...(clearApiKey ? { clear_api_key: true } : {}),
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
      await refresh(userOffset);
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
      await refresh(userOffset);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeletingKey(null);
    }
  }

  async function onSaveUserAccess(user: AdminModelAccessUserOut) {
    setError(null);
    setSavingUserId(user.user_id);
    try {
      await apiJson<AdminModelAccessUserOut>(`/admin/model-access/users/${user.user_id}`, {
        method: "PUT",
        body: {
          model_allowlist_override: userAccessDrafts[user.user_id] ?? user.model_allowlist_override,
        } satisfies AdminModelAccessUpdateRequest,
      });
      await refresh(userOffset);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSavingUserId(null);
    }
  }

  if (me && !isAdmin) {
    return (
      <main className="trials-page-main">
        <section className="block">
          <h2 style={{ margin: 0, fontSize: 28 }}>{t("page.heading")}</h2>
          <p style={{ marginTop: 10, fontSize: 16, color: "var(--red)" }}>
            {t("page.accessDenied")}
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="trials-page-main">
      <SEO title={t("page.title")} description={t("page.description")} noindex />
      <section className="trials-head block">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p style={{ fontSize: 13, color: "var(--muted)", letterSpacing: "0.8px" }}>
              {t("page.header")}
            </p>
            <h1>{t("page.heading")}</h1>
            <p>
              {t("page.intro")}
            </p>
          </div>
          <button
            type="button"
            onClick={() => refresh(userOffset)}
            className="newrun-action-btn ghost"
            disabled={!isAdmin || loading}
          >
            {loading ? t("actions.loading") : t("actions.refresh")}
          </button>
        </div>
      </section>

      {error ? (
        <div
          style={{
            border: "2px solid var(--red)",
            background: "#fde8e6",
            padding: "8px 10px",
            fontSize: 16,
            color: "var(--red)",
          }}
        >
          {error}
        </div>
      ) : null}

      <section className="block">
        <h2 style={{ margin: "0 0 12px 0", fontSize: 24 }}>{t("form.addModel")}</h2>
        <form onSubmit={onCreate} className="newrun-form">
          <div className="newrun-grid">
            <div className="newrun-field">
              <span>{t("form.modelKey")}</span>
              <input
                value={create.model_key}
                onChange={(e) =>
                  setCreate((p) => ({ ...p, model_key: e.target.value }))
                }
                placeholder={t("form.modelKeyPlaceholder")}
                required
              />
            </div>
            <div className="newrun-field">
              <span>{t("form.label")}</span>
              <input
                value={create.label ?? ""}
                onChange={(e) =>
                  setCreate((p) => ({ ...p, label: e.target.value }))
                }
                placeholder={t("form.labelPlaceholder")}
              />
            </div>
          </div>
          <div className="newrun-field">
            <span>{t("form.apiBaseUrl")}</span>
            <input
              value={create.api_base_url ?? ""}
              onChange={(e) =>
                setCreate((p) => ({ ...p, api_base_url: e.target.value }))
              }
              placeholder={t("form.apiBaseUrlPlaceholder")}
            />
          </div>
          <div className="newrun-field">
            <span>{t("form.apiKey")}</span>
            <input
              type="password"
              value={create.api_key ?? ""}
              onChange={(e) =>
                setCreate((p) => ({ ...p, api_key: e.target.value }))
              }
              placeholder={t("form.apiKeyPlaceholder")}
              autoComplete="new-password"
            />
          </div>
          <label
            className="flex items-center gap-3"
            style={{
              border: "2px solid #404040",
              background: "#f9f9f9",
              padding: "8px 10px",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={Boolean(create.enabled)}
              onChange={(e) =>
                setCreate((p) => ({ ...p, enabled: e.target.checked }))
              }
              style={{ width: 16, height: 16 }}
            />
            <span style={{ fontSize: 16 }}>{t("form.enabled")}</span>
          </label>
          <div className="newrun-actions" style={{ justifyContent: "flex-end" }}>
            <button type="submit" className="newrun-action-btn" disabled={loading}>
              {t("actions.add")}
            </button>
          </div>
        </form>
      </section>

      <section className="block">
        <h2 style={{ margin: "0 0 12px 0", fontSize: 24 }}>{t("models.heading")}</h2>
        <div style={{ display: "grid", gap: 10 }}>
          {models.length === 0 ? (
            <div style={{ fontSize: 16, color: "var(--muted)" }}>
              {t("models.empty")}
            </div>
          ) : null}
          {models.map((m) => {
            const d = drafts[m.model_key] ?? {};
            const label = d.label ?? m.label ?? "";
            const apiBaseUrl = d.api_base_url ?? m.api_base_url ?? "";
            const apiKeyDraft = d.api_key ?? "";
            const clearApiKey = Boolean(d.clear_api_key);
            const enabled = d.enabled ?? m.enabled;
            return (
              <div
                key={m.model_key}
                style={{
                  border: "2px solid var(--line)",
                  background: "#f8f8f8",
                  padding: 12,
                }}
              >
                <div className="newrun-grid" style={{ alignItems: "end" }}>
                  <div>
                    <span
                      style={{
                        fontSize: 12,
                        letterSpacing: "0.8px",
                        color: "var(--muted)",
                      }}
                    >
                      {t("status.modelKey")}
                    </span>
                    <div style={{ fontSize: 18, marginTop: 4 }}>{m.model_key}</div>
                  </div>
                  <div className="newrun-field">
                    <span>{t("form.label")}</span>
                    <input
                      value={label}
                      onChange={(e) =>
                        setDrafts((p) => ({
                          ...p,
                          [m.model_key]: { ...p[m.model_key], label: e.target.value },
                        }))
                      }
                    />
                  </div>
                </div>

                <div className="newrun-field" style={{ marginTop: 10 }}>
                  <span>{t("form.apiBaseUrl")}</span>
                  <input
                    value={apiBaseUrl}
                    onChange={(e) =>
                      setDrafts((p) => ({
                        ...p,
                        [m.model_key]: { ...p[m.model_key], api_base_url: e.target.value },
                      }))
                    }
                  />
                </div>

                <div
                  className="newrun-grid"
                  style={{ marginTop: 10, alignItems: "end" }}
                >
                  <div className="newrun-field">
                    <span className="flex items-center justify-between gap-3">
                      <span>{t("form.apiKey")}</span>
                      <span
                        style={{
                          fontSize: 11,
                          letterSpacing: "0.18em",
                          color: "var(--muted)",
                        }}
                      >
                        {m.has_api_key && !clearApiKey ? t("status.stored") : t("status.notStored")}
                      </span>
                    </span>
                    <input
                      type="password"
                      value={apiKeyDraft}
                      onChange={(e) =>
                        setDrafts((p) => ({
                          ...p,
                          [m.model_key]: {
                            ...p[m.model_key],
                            api_key: e.target.value,
                            clear_api_key: false,
                          },
                        }))
                      }
                      placeholder={
                        m.has_api_key
                          ? t("form.apiKeyReplacePrompt")
                          : t("form.apiKeyStorePrompt")
                      }
                      autoComplete="new-password"
                    />
                  </div>

                  <label
                    className="flex items-center gap-3"
                    style={{
                      border: "2px solid #404040",
                      background: "#f9f9f9",
                      padding: "8px 10px",
                      cursor: "pointer",
                      height: "fit-content",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={clearApiKey}
                      onChange={(e) =>
                        setDrafts((p) => ({
                          ...p,
                          [m.model_key]: {
                            ...p[m.model_key],
                            api_key: e.target.checked
                              ? ""
                              : p[m.model_key]?.api_key,
                            clear_api_key: e.target.checked,
                          },
                        }))
                      }
                      style={{ width: 16, height: 16 }}
                    />
                    <span style={{ fontSize: 14 }}>{t("form.clearStoredKey")}</span>
                  </label>
                </div>

                <div
                  className="flex items-center justify-between gap-3"
                  style={{ marginTop: 12 }}
                >
                  <label
                    className="flex items-center gap-3"
                    style={{
                      border: "2px solid #404040",
                      background: "#f9f9f9",
                      padding: "8px 10px",
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={Boolean(enabled)}
                      onChange={(e) =>
                        setDrafts((p) => ({
                          ...p,
                          [m.model_key]: { ...p[m.model_key], enabled: e.target.checked },
                        }))
                      }
                      style={{ width: 16, height: 16 }}
                    />
                    <span style={{ fontSize: 16 }}>{t("form.enabled")}</span>
                  </label>
                  <div className="newrun-actions">
                    <button
                      type="button"
                      onClick={() => onSave(m.model_key)}
                      className="newrun-action-btn"
                      disabled={savingKey === m.model_key}
                    >
                      {savingKey === m.model_key ? t("actions.saving") : t("actions.save")}
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(m.model_key)}
                      className="newrun-action-btn ghost"
                      style={{
                        color: "var(--red)",
                        borderColor: "var(--red)",
                      }}
                      disabled={deletingKey === m.model_key}
                    >
                      {deletingKey === m.model_key ? t("actions.deleting") : t("actions.delete")}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="block">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 style={{ margin: "0 0 8px 0", fontSize: 24 }}>
              {t("users.heading")}
            </h2>
            <p style={{ margin: 0, fontSize: 17, color: "#555" }}>
              {t("users.intro")}{" "}
              <span
                style={{
                  border: "1px solid #888",
                  background: "#fff",
                  padding: "2px 6px",
                  fontSize: 14,
                }}
              >
                +deepseekv3,-gemini-3-pro
              </span>{" "}
              {t("users.introSuffix")}
            </p>
          </div>
          <div
            style={{
              border: "2px solid var(--line)",
              background: "#fdfdfd",
              padding: "8px 10px",
              fontSize: 14,
              color: "var(--muted)",
              whiteSpace: "nowrap",
            }}
          >
            {modelAccess?.default_allows_all_models
              ? t("users.defaultAllowsAll")
              : t("users.defaultAllowlist", { 
                  models: modelAccess?.default_allowlist_model_keys.join(", ") || t("users.defaultAllowlistNone")
                })}
          </div>
        </div>

        <div style={{ marginTop: 16, display: "grid", gap: 10 }}>
          <div
            className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between"
            style={{
              border: "2px solid var(--line)",
              background: "#ededed",
              padding: "8px 10px",
              fontSize: 14,
              color: "var(--muted)",
            }}
          >
            <span>
              {modelAccess 
                ? t("users.showingTotal", { 
                    count: modelAccess.users.length, 
                    offset: modelAccess.offset, 
                    total: modelAccess.total_users 
                  })
                : t("users.showing", { count: 0, offset: 0 })}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() =>
                  refresh(Math.max(0, userOffset - USER_PAGE_SIZE))
                }
                className="newrun-action-btn ghost"
                style={{ fontSize: 14, padding: "5px 10px" }}
                disabled={loading || userOffset === 0}
              >
                {t("actions.previous")}
              </button>
              <button
                type="button"
                onClick={() => refresh(userOffset + USER_PAGE_SIZE)}
                className="newrun-action-btn ghost"
                style={{ fontSize: 14, padding: "5px 10px" }}
                disabled={loading || !modelAccess?.has_more}
              >
                {t("actions.next")}
              </button>
            </div>
          </div>

          {modelAccess?.users.length ? null : (
            <div style={{ fontSize: 16, color: "var(--muted)" }}>
              {t("users.empty")}
            </div>
          )}

          {modelAccess?.users.map((user) => {
            const draftValue =
              userAccessDrafts[user.user_id] ??
              user.model_allowlist_override ??
              "";
            return (
              <div
                key={user.user_id}
                style={{
                  border: "2px solid var(--line)",
                  background: "#f8f8f8",
                  padding: 12,
                }}
              >
                <div
                  className="grid gap-4"
                  style={{
                    gridTemplateColumns: "minmax(0,1.2fr) minmax(0,1.5fr) minmax(0,1fr) auto",
                    alignItems: "end",
                  }}
                >
                  <div style={{ display: "grid", gap: 4 }}>
                    <div style={{ fontSize: 18 }}>
                      {user.display_name || user.email || user.user_id}
                    </div>
                    <div style={{ fontSize: 13, color: "var(--muted)" }}>
                      {user.email || user.user_id}
                    </div>
                  </div>

                  <div className="newrun-field">
                    <span>{t("form.modelAllowlistOverride")}</span>
                    <input
                      value={draftValue}
                      onChange={(e) =>
                        setUserAccessDrafts((prev) => ({
                          ...prev,
                          [user.user_id]: e.target.value,
                        }))
                      }
                      placeholder={t("form.overridePlaceholder")}
                    />
                  </div>

                  <div style={{ display: "grid", gap: 4, fontSize: 14 }}>
                    <span style={{ color: "var(--ink)" }}>{t("status.selectableNow")}</span>
                    <span style={{ color: "var(--muted)" }}>
                      {user.selectable_model_keys.join(", ") || t("status.stubOnly")}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => onSaveUserAccess(user)}
                    className="newrun-action-btn"
                    style={{ fontSize: 16, padding: "6px 12px" }}
                    disabled={savingUserId === user.user_id}
                  >
                    {savingUserId === user.user_id ? t("actions.saving") : t("actions.save")}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </main>
  );
}
