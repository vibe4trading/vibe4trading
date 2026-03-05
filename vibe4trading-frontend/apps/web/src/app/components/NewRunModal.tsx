"use client";

import * as React from "react";

import { PromptInput } from "@/app/components/PromptInput";
import { ModelPublicOut } from "@/app/lib/v4t";

type NewRunModalProps = {
  open: boolean;
  markets: string[];
  models: ModelPublicOut[];

  marketsLoaded?: boolean;
  modelsLoaded?: boolean;

  marketId: string;
  modelKey: string;
  promptText: string;

  onChangeMarketId: (v: string) => void;
  onChangeModelKey: (v: string) => void;
  onChangePromptText: (v: string) => void;

  onClose: () => void;
  onSubmit: () => void;

  submitting?: boolean;
  submitError?: string | null;
};

export function NewRunModal({
  open,
  markets,
  models,
  marketsLoaded,
  modelsLoaded,
  marketId,
  modelKey,
  promptText,
  onChangeMarketId,
  onChangeModelKey,
  onChangePromptText,
  onClose,
  onSubmit,
  submitting,
  submitError,
}: NewRunModalProps) {
  const [error, setError] = React.useState<string | null>(null);
  const firstFieldRef = React.useRef<HTMLSelectElement | null>(null);
  const previouslyFocused = React.useRef<HTMLElement | null>(null);
  const panelRef = React.useRef<HTMLDivElement | null>(null);
  const titleId = React.useId();
  const descId = React.useId();

  React.useEffect(() => {
    if (!open) return;

    setError(null);

    previouslyFocused.current = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";

    const t = window.setTimeout(() => {
      firstFieldRef.current?.focus();
    }, 0);

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (submitting) return;
        onClose();
        return;
      }

      if (e.key === "Tab") {
        const panel = panelRef.current;
        if (!panel) return;

        const focusables = Array.from(
          panel.querySelectorAll<HTMLElement>(
            'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])',
          ),
        ).filter((el) => !el.hasAttribute("disabled") && el.tabIndex !== -1);
        if (focusables.length === 0) return;

        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement as HTMLElement | null;

        if (e.shiftKey) {
          if (!active || active === first || !panel.contains(active)) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (active === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.clearTimeout(t);
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
      previouslyFocused.current?.focus?.();
    };
  }, [open, onClose, submitting]);

  React.useEffect(() => {
    if (!open) return;
    setError(null);
  }, [open, marketId, modelKey, promptText]);

  if (!open) return null;

  const arenaConfigured = markets.length > 0;
  const modelsConfigured = models.length > 0;
  const marketsReady = Boolean(marketsLoaded ?? arenaConfigured);
  const modelsReady = Boolean(modelsLoaded ?? modelsConfigured);

  function validate() {
    if (!marketsReady) return "Loading coins...";
    if (!arenaConfigured) return "Tournament markets are not configured.";
    if (!marketId) return "Select a coin.";
    if (!modelsReady) return "Loading models...";
    if (!modelsConfigured) return "No models are configured.";
    if (!modelKey.trim()) return "Model is required.";
    if (!promptText.trim()) return "Prompt is required.";
    return null;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;
    const msg = validate();
    if (msg) {
      setError(msg);
      return;
    }
    setError(null);
    onSubmit();
  }

  return (
    <div
      className="fixed inset-0 z-40 flex items-end justify-center px-5 py-6 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-label="Start new run"
      aria-describedby={descId}
    >
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onMouseDown={() => {
          if (submitting) return;
          onClose();
        }}
        aria-hidden="true"
      />

      <div
        ref={panelRef}
        className="relative w-full max-w-2xl max-h-[calc(100vh-3rem)] overflow-hidden rounded-3xl border border-white/10 bg-[color:var(--surface)] shadow-[0_20px_80px_rgba(0,0,0,0.6)] flex flex-col"
      >
        <div className="flex items-start justify-between gap-4 border-b border-white/10 bg-white/5 px-6 py-5">
          <div>
            <div className="text-xs font-bold tracking-widest text-[color:var(--accent-2)]">
              TOURNAMENT RUN
            </div>
            <h3 id={titleId} className="mt-1 font-display text-2xl tracking-tight text-white">
              Start a new run
            </h3>
            <p id={descId} className="mt-2 text-sm text-zinc-400">
              Choose a coin + model, paste your prompt, then we&apos;ll spin up the scenario windows.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={Boolean(submitting)}
            className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-zinc-200 transition-all hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            Close
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-6 py-6">
          {error || submitError ? (
            <div className="mb-5 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm font-medium text-rose-200">
              {error ?? submitError}
            </div>
          ) : null}

          <div className="grid gap-5 md:grid-cols-2">
            <label className="grid gap-1.5 text-sm">
              <span className="text-zinc-400 font-medium">coin</span>
              <div className="relative">
                <select
                  ref={firstFieldRef}
                  value={marketId}
                  onChange={(e) => onChangeMarketId(e.target.value)}
                  className="w-full h-11 appearance-none rounded-xl border border-white/10 bg-black/40 px-4 font-mono text-xs text-white focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all disabled:opacity-60"
                  disabled={!arenaConfigured || Boolean(submitting)}
                  required
                >
                  {arenaConfigured ? (
                    markets.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))
                  ) : (
                    <option value="" disabled>
                      Configure backend datasets
                    </option>
                  )}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-zinc-500">
                  <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
                    <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                  </svg>
                </div>
              </div>
            </label>

            <label className="grid gap-1.5 text-sm">
              <span className="text-zinc-400 font-medium">model</span>
              <div className="relative">
                <select
                  value={modelKey}
                  onChange={(e) => onChangeModelKey(e.target.value)}
                  className="w-full h-11 appearance-none rounded-xl border border-white/10 bg-black/40 px-4 font-mono text-xs text-white focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all disabled:opacity-60"
                  disabled={!modelsConfigured || Boolean(submitting)}
                  required
                >
                  {modelsConfigured ? (
                    models.map((m) => (
                      <option key={m.model_key} value={m.model_key}>
                        {m.label ? `${m.label} (${m.model_key})` : m.model_key}
                      </option>
                    ))
                  ) : (
                    <option value="" disabled>
                      Configure backend models
                    </option>
                  )}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-zinc-500">
                  <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
                    <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                  </svg>
                </div>
              </div>
            </label>

            <div className="md:col-span-2">
              <PromptInput value={promptText} onChange={onChangePromptText} mode="pro" />
            </div>

            <div className="md:col-span-2 mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-end">
              <button
                type="button"
                onClick={onClose}
                disabled={Boolean(submitting)}
                className="rounded-full border border-white/15 bg-white/5 px-7 py-3 text-sm font-semibold text-white transition-all hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={Boolean(submitting) || !arenaConfigured || !modelsConfigured}
                className="rounded-full bg-white px-7 py-3 text-sm font-bold text-black transition-all hover:bg-zinc-200 hover:shadow-[0_0_22px_rgba(255,255,255,0.22)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "Starting..." : "Start run"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
