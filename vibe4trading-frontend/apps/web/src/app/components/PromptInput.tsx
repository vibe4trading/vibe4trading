"use client";

import { useState } from "react";

type PromptMode = "noob" | "pro";

interface PromptInputProps {
  value: string;
  onChange: (value: string) => void;
  mode?: PromptMode;
}

const NOOB_TEMPLATE = {
  tradingStyle: ["aggressive", "conservative", "balanced"],
  timeHorizon: ["frequent", "medium-term", "long-term"],
  riskTolerance: ["high", "moderate", "low"],
};

export function PromptInput({ value, onChange, mode: initialMode = "noob" }: PromptInputProps) {
  const [mode, setMode] = useState<PromptMode>(initialMode);
  const [noobSelections, setNoobSelections] = useState({
    tradingStyle: "balanced",
    timeHorizon: "medium-term",
    riskTolerance: "moderate",
  });

  const buildNoobPrompt = (selections: typeof noobSelections) => {
    return `You are a trading decision engine. I'm a ${selections.tradingStyle} trader. I play ${selections.timeHorizon} trading with ${selections.riskTolerance} risk tolerance.

Analyze the market data and sentiment, then output a JSON decision with your target exposure (0-1 for spot long-only), confidence, key signals, and rationale.

Output format:
{"schema_version":1,"targets":{"<market_id>":0.25},"next_check_seconds":600,"confidence":0.6,"key_signals":["..."],"rationale":"..."}`;
  };

  const handleNoobChange = (field: keyof typeof noobSelections, val: string) => {
    const updated = { ...noobSelections, [field]: val };
    setNoobSelections(updated);
    onChange(buildNoobPrompt(updated));
  };

  const handleModeSwitch = (newMode: PromptMode) => {
    setMode(newMode);
    if (newMode === "noob" && !value) {
      onChange(buildNoobPrompt(noobSelections));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => handleModeSwitch("noob")}
          className={`rounded-xl px-4 py-2 text-sm font-medium transition-all ${
            mode === "noob"
              ? "bg-[color:var(--accent)] text-white shadow-[0_0_12px_var(--accent-glow)]"
              : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white"
          }`}
        >
          Noob Mode
        </button>
        <button
          type="button"
          onClick={() => handleModeSwitch("pro")}
          className={`rounded-xl px-4 py-2 text-sm font-medium transition-all ${
            mode === "pro"
              ? "bg-[color:var(--accent)] text-white shadow-[0_0_12px_var(--accent-glow)]"
              : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white"
          }`}
        >
          Pro Mode
        </button>
      </div>

      {mode === "noob" ? (
        <div className="space-y-4 rounded-2xl border border-[color:var(--border)] bg-white/5 p-5">
          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-300">Trading Style</label>
            <select
              value={noobSelections.tradingStyle}
              onChange={(e) => handleNoobChange("tradingStyle", e.target.value)}
              className="w-full h-11 appearance-none rounded-xl border border-white/10 bg-black/40 px-4 text-sm text-white focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all"
            >
              {NOOB_TEMPLATE.tradingStyle.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-300">Time Horizon</label>
            <select
              value={noobSelections.timeHorizon}
              onChange={(e) => handleNoobChange("timeHorizon", e.target.value)}
              className="w-full h-11 appearance-none rounded-xl border border-white/10 bg-black/40 px-4 text-sm text-white focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all"
            >
              {NOOB_TEMPLATE.timeHorizon.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-300">Risk Tolerance</label>
            <select
              value={noobSelections.riskTolerance}
              onChange={(e) => handleNoobChange("riskTolerance", e.target.value)}
              className="w-full h-11 appearance-none rounded-xl border border-white/10 bg-black/40 px-4 text-sm text-white focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all"
            >
              {NOOB_TEMPLATE.riskTolerance.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>

          <div className="mt-4 rounded-xl bg-black/30 p-4">
            <p className="text-xs font-medium text-zinc-400">Generated Prompt Preview:</p>
            <pre className="mt-2 whitespace-pre-wrap text-xs text-zinc-300">{value}</pre>
          </div>
        </div>
      ) : (
        <div>
          <label className="mb-2 block text-sm font-medium text-zinc-300">Prompt Text</label>
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            rows={12}
            placeholder="Enter your custom prompt..."
            className="w-full rounded-2xl border border-white/10 bg-black/40 p-4 font-mono text-sm text-white placeholder-zinc-600 focus:border-[color:var(--accent)] focus:outline-none focus:ring-1 focus:ring-[color:var(--accent)] transition-all"
          />
        </div>
      )}
    </div>
  );
}
