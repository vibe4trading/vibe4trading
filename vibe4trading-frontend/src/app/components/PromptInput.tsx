import { useEffect, useMemo, useRef, useState } from "react";

type PromptMode = "noob" | "pro";

type PromptVariant = "dark" | "light";

interface PromptInputProps {
  value: string;
  onChange: (value: string) => void;
  mode?: PromptMode;
  variant?: PromptVariant;
}

const NOOB_TEMPLATE = {
  tradingStyle: ["aggressive", "conservative", "balanced"],
  timeHorizon: ["frequent", "medium-term", "long-term"],
  riskTolerance: ["high", "moderate", "low"],
} as const;

type NoobSelections = {
  tradingStyle: (typeof NOOB_TEMPLATE.tradingStyle)[number];
  timeHorizon: (typeof NOOB_TEMPLATE.timeHorizon)[number];
  riskTolerance: (typeof NOOB_TEMPLATE.riskTolerance)[number];
};

function buildNoobPrompt(selections: NoobSelections) {
  return `You are a trading decision engine. I'm a ${selections.tradingStyle} trader. I play ${selections.timeHorizon} trading with ${selections.riskTolerance} risk tolerance.

Analyze the market data and sentiment, then make trading decisions that fit this style, time horizon, and risk profile.`;
}

export function PromptInput({
  value,
  onChange,
  mode: initialMode = "noob",
  variant = "dark",
}: PromptInputProps) {
  const [mode, setMode] = useState<PromptMode>(initialMode);
  const [noobSelections, setNoobSelections] = useState<NoobSelections>({
    tradingStyle: "balanced",
    timeHorizon: "medium-term",
    riskTolerance: "moderate",
  });
  const initializedRef = useRef(false);

  useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);

  const isLight = variant === "light";
  const generatedPrompt = useMemo(
    () => buildNoobPrompt(noobSelections),
    [noobSelections],
  );

  useEffect(() => {
    if (mode === "noob" && !value.trim() && !initializedRef.current) {
      initializedRef.current = true;
      onChange(generatedPrompt);
    }
  }, [mode, generatedPrompt, onChange, value]);

  const toggleBase = isLight
    ? "flex-1 border border-[#2f2f2f]/35 bg-transparent px-4 py-3 text-[12px] uppercase tracking-[0.22em] text-[#222] transition-colors hover:bg-[#111]/6"
    : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white";
  const toggleActive = isLight
    ? "flex-1 border border-[#161616] bg-[#161616] px-4 py-3 text-[12px] uppercase tracking-[0.22em] text-[#f7f3eb]"
    : "bg-[color:var(--accent)] text-white shadow-[0_0_12px_var(--accent-glow)]";
  const panelClass = isLight
    ? "border border-[#2f2f2f]/22 bg-[#111]/[0.025] p-5"
    : "rounded-2xl border border-[color:var(--border)] bg-white/5 p-5";
  const labelClass = isLight
    ? "mb-2 block text-[11px] font-medium uppercase tracking-[0.22em] text-[#585858]"
    : "mb-2 block text-sm font-medium text-zinc-300";
  const selectClass = isLight
    ? "w-full h-12 appearance-none border border-[#2f2f2f]/35 bg-[#fbfaf7] px-4 text-[13px] uppercase tracking-[0.12em] text-[#151515] focus:outline-none focus:border-[#151515] transition-colors"
    : "w-full h-11 appearance-none rounded-xl border border-white/10 bg-black/40 px-4 text-sm text-white focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all";
  const previewClass = isLight
    ? "mt-4 border border-[#2f2f2f]/28 bg-[#fbfaf7] p-4"
    : "mt-4 rounded-xl bg-black/30 p-4";
  const previewTextClass = isLight
    ? "mt-3 whitespace-pre-wrap text-[11px] leading-6 text-[#444]"
    : "mt-2 whitespace-pre-wrap text-xs text-zinc-300";
  const textareaClass = isLight
    ? "min-h-[260px] w-full resize-y border border-[#2f2f2f]/35 bg-[#fbfaf7] p-4 text-[12px] leading-6 text-[#181818] placeholder-[#888] focus:outline-none focus:border-[#181818] transition-colors"
    : "w-full rounded-2xl border border-white/10 bg-black/40 p-4 font-mono text-sm text-white placeholder-zinc-600 focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all";
  const darkToggleClass = "rounded-xl px-4 py-2 text-sm font-medium transition-all";

  const handleNoobChange = <K extends keyof NoobSelections>(
    field: K,
    nextValue: NoobSelections[K],
  ) => {
    const updated = { ...noobSelections, [field]: nextValue };
    setNoobSelections(updated);
    onChange(buildNoobPrompt(updated));
  };

  const handleModeSwitch = (nextMode: PromptMode) => {
    setMode(nextMode);
    if (nextMode === "noob" && !value.trim()) {
      onChange(generatedPrompt);
    }
  };

  return (
    <div className="space-y-4">
      <div className={isLight ? "flex gap-0 border border-[#2f2f2f]/30" : "flex gap-2"} data-tour="arena-prompt-mode">
        <button
          type="button"
          onClick={() => handleModeSwitch("noob")}
          className={
            isLight
              ? mode === "noob"
                ? toggleActive
                : toggleBase
              : `${darkToggleClass} ${mode === "noob" ? toggleActive : toggleBase}`
          }
        >
          {isLight ? "Beginner Mode" : "Noob Mode"}
        </button>
        <button
          type="button"
          onClick={() => handleModeSwitch("pro")}
          className={
            isLight
              ? mode === "pro"
                ? toggleActive
                : toggleBase
              : `${darkToggleClass} ${mode === "pro" ? toggleActive : toggleBase}`
          }
        >
          Pro Mode
        </button>
      </div>

      {mode === "noob" ? (
        <div className={`space-y-4 ${panelClass}`} data-tour="arena-beginner-dropdowns">
          <div className={isLight ? "grid gap-4 md:grid-cols-3" : "space-y-4"}>
            <div>
              <label className={labelClass}>Trading Style</label>
              <select
                value={noobSelections.tradingStyle}
                onChange={(e) =>
                  handleNoobChange(
                    "tradingStyle",
                    e.target.value as NoobSelections["tradingStyle"],
                  )
                }
                className={selectClass}
              >
                {NOOB_TEMPLATE.tradingStyle.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className={labelClass}>Time Horizon</label>
              <select
                value={noobSelections.timeHorizon}
                onChange={(e) =>
                  handleNoobChange(
                    "timeHorizon",
                    e.target.value as NoobSelections["timeHorizon"],
                  )
                }
                className={selectClass}
              >
                {NOOB_TEMPLATE.timeHorizon.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className={labelClass}>Risk Tolerance</label>
              <select
                value={noobSelections.riskTolerance}
                onChange={(e) =>
                  handleNoobChange(
                    "riskTolerance",
                    e.target.value as NoobSelections["riskTolerance"],
                  )
                }
                className={selectClass}
              >
                {NOOB_TEMPLATE.riskTolerance.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className={previewClass}>
            <div className="flex items-center justify-between gap-3">
              <p
                className={
                  isLight
                    ? "text-[11px] font-medium uppercase tracking-[0.22em] text-[#585858]"
                    : "text-xs font-medium text-zinc-400"
                }
              >
                Generated Prompt Preview
              </p>
              {isLight ? (
                <button
                  type="button"
                  onClick={() => { try { navigator.clipboard.writeText(value || generatedPrompt); } catch { /* clipboard unavailable */ } }}
                  className="border border-[#2f2f2f]/30 px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-[#222] transition-colors hover:bg-[#111]/6"
                >
                  Copy
                </button>
              ) : null}
            </div>
            <pre className={previewTextClass}>{value || generatedPrompt}</pre>
          </div>
        </div>
      ) : (
        <div className={isLight ? "space-y-4 border border-[#2f2f2f]/22 bg-[#111]/[0.025] p-5" : ""}>
          {isLight ? (
            <p className="text-[11px] uppercase tracking-[0.18em] text-[#666]">
              Write your own trading prompt. Full control over constraints, position sizing, and risk handling.
            </p>
          ) : null}
          <div>
            <label className={labelClass}>Prompt Text</label>
            <textarea
              value={value}
              onChange={(e) => onChange(e.target.value)}
              rows={12}
              placeholder="You are a crypto trading agent. Define your strategy..."
              className={textareaClass}
            />
          </div>
          {isLight ? (
            <p className="text-[10px] uppercase tracking-[0.16em] text-[#777]">
              Tip: be explicit about risk limits, leverage, holding period, and token preference.
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
}
