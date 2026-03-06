"use client";

import * as React from "react";

import { PromptInput } from "@/app/components/PromptInput";
import { useModalA11y } from "@/app/hooks/useModalA11y";
import { ModelPublicOut } from "@/app/lib/v4t";

function pairName(marketId: string) {
  const parts = marketId.split(":");
  return parts[parts.length - 1] ?? marketId;
}

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
  const { panelRef } = useModalA11y(open, submitting ? () => {} : onClose);
  const titleId = React.useId();
  const descId = React.useId();

  React.useEffect(() => {
    if (!open) return;
    setError(null);
    const timeoutId = window.setTimeout(() => {
      firstFieldRef.current?.focus();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [open]);

  React.useEffect(() => {
    if (!open) return;
    setError(null);
  }, [open, marketId, modelKey, promptText]);

  if (!open) return null;

  const arenaConfigured = markets.length > 0;
  const modelsConfigured = models.length > 0;
  const selectableModelsConfigured = models.some((model) => model.selectable);
  const marketsReady = Boolean(marketsLoaded ?? arenaConfigured);
  const modelsReady = Boolean(modelsLoaded ?? modelsConfigured);
  const selectedModel = models.find((model) => model.model_key === modelKey) ?? null;

  function validate() {
    if (!marketsReady) return "Loading coins...";
    if (!arenaConfigured) return "Tournament markets are not configured.";
    if (!marketId) return "Select a coin.";
    if (!modelsReady) return "Loading models...";
    if (!modelsConfigured) return "No models are configured.";
    if (!selectableModelsConfigured) return "No models are enabled for your account.";
    if (!modelKey.trim()) return "Model is required.";
    if (!selectedModel?.selectable) return selectedModel?.disabled_reason ?? "Model is not available.";
    if (!promptText.trim()) return "Prompt is required.";
    return null;
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (submitting) return;
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    onSubmit();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-label="Start new run"
      aria-describedby={descId}
    >
      <div
        className="absolute inset-0 bg-[rgba(12,12,12,0.76)] backdrop-blur-[2px]"
        onMouseDown={() => {
          if (!submitting) onClose();
        }}
        aria-hidden="true"
      />

      <div
        ref={panelRef as React.RefObject<HTMLDivElement>}
        className="relative flex max-h-[calc(100vh-2rem)] w-full max-w-2xl flex-col overflow-hidden border border-[#161616] bg-[#f4f1e8] text-[#141414] shadow-[0_24px_80px_rgba(0,0,0,0.4)]"
      >
        <div className="border-b border-[#161616]/18 px-6 py-6 md:px-8">
          <button
            type="button"
            onClick={onClose}
            disabled={Boolean(submitting)}
            className="absolute right-5 top-5 border border-[#161616]/30 px-3 py-2 text-[11px] uppercase tracking-[0.24em] text-[#222] transition-colors hover:bg-[#161616]/6 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Close
          </button>

          <div className="pr-20">
            <p className="text-[12px] uppercase tracking-[0.32em] text-[#5c6bf3]">
              Strategy Config
            </p>
            <h3 id={titleId} className="mt-3 text-[26px] uppercase tracking-[0.12em] md:text-[30px]">
              Start New Run
            </h3>
            <p id={descId} className="mt-3 max-w-2xl text-[13px] leading-6 text-[#5d5d5d]">
              Configure the pair, model, and prompt, then benchmark the strategy across the historical trial set.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-6 py-6 md:px-8 md:py-7">
            {error || submitError ? (
              <div className="mb-5 border border-[#ae4032] bg-[#f5dfd7] px-4 py-3 text-[12px] uppercase tracking-[0.14em] text-[#8f2d22]">
                {error ?? submitError}
              </div>
            ) : null}

            <div className="grid gap-5">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2">
                  <span className="text-[11px] uppercase tracking-[0.22em] text-[#585858]">Pair</span>
                  <div className="relative">
                    <select
                      ref={firstFieldRef}
                      value={marketId}
                      onChange={(e) => onChangeMarketId(e.target.value)}
                      className="h-12 w-full appearance-none border border-[#2f2f2f]/35 bg-[#fbfaf7] px-4 text-[13px] uppercase tracking-[0.12em] text-[#151515] focus:outline-none focus:border-[#151515] transition-colors disabled:opacity-60"
                      disabled={!arenaConfigured || Boolean(submitting)}
                      required
                    >
                      {arenaConfigured ? (
                        markets.map((market) => (
                          <option key={market} value={market}>
                            {pairName(market)}
                          </option>
                        ))
                      ) : (
                        <option value="" disabled>
                          Configure backend datasets
                        </option>
                      )}
                    </select>
                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-[#555]">
                      <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
                        <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                      </svg>
                    </div>
                  </div>
                </label>

                <label className="grid gap-2">
                  <span className="text-[11px] uppercase tracking-[0.22em] text-[#585858]">AI Model</span>
                  <div className="relative">
                    <select
                      value={modelKey}
                      onChange={(e) => onChangeModelKey(e.target.value)}
                      className="h-12 w-full appearance-none border border-[#2f2f2f]/35 bg-[#fbfaf7] px-4 text-[13px] uppercase tracking-[0.12em] text-[#151515] focus:outline-none focus:border-[#151515] transition-colors disabled:opacity-60"
                      disabled={!modelsConfigured || Boolean(submitting)}
                      required
                    >
                      {modelsConfigured ? (
                        models.map((model) => (
                          <option
                            key={model.model_key}
                            value={model.model_key}
                            disabled={!model.selectable}
                          >
                            {model.label ? `${model.label} (${model.model_key})` : model.model_key}
                            {model.selectable ? "" : ` - ${model.disabled_reason ?? "Unavailable"}`}
                          </option>
                        ))
                      ) : (
                        <option value="" disabled>
                          Configure backend models
                        </option>
                      )}
                    </select>
                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-[#555]">
                      <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
                        <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                      </svg>
                    </div>
                  </div>
                  {selectedModel && !selectedModel.selectable ? (
                    <p className="text-[11px] uppercase tracking-[0.14em] text-[#8f2d22]">
                      {selectedModel.disabled_reason ?? "Model is unavailable."}
                    </p>
                  ) : null}
                </label>
              </div>

              <PromptInput
                value={promptText}
                onChange={onChangePromptText}
                mode="noob"
                variant="light"
              />
            </div>
          </div>

          <div className="border-t border-[#161616]/16 bg-[#f4f1e8] px-6 py-5 md:px-8">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <p className="text-[11px] uppercase tracking-[0.18em] text-[#676767]">
                Public submissions appear in trials and leaderboard views.
              </p>
              <div className="flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={Boolean(submitting)}
                  className="border border-[#161616]/30 px-5 py-3 text-[11px] uppercase tracking-[0.24em] text-[#222] transition-colors hover:bg-[#161616]/6 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={Boolean(submitting) || !arenaConfigured || !selectableModelsConfigured}
                  className="border border-[#161616] bg-[#161616] px-6 py-3 text-[11px] uppercase tracking-[0.26em] text-[#f7f3eb] transition-colors hover:bg-[#303030] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {submitting ? "Starting..." : "Start Run ->"}
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
