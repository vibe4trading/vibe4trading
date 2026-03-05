import React, { useEffect, useState } from "react";

export function CircularLoading({ status }: { status: string }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (status !== "running") return;
    // Simulate some progress
    const interval = setInterval(() => {
      setProgress((p) => {
        if (p >= 98) return p;
        const inc = Math.random() * 5 + 1;
        return Math.min(p + inc, 98);
      });
    }, 400);
    return () => clearInterval(interval);
  }, [status]);

  return (
    <div className="flex h-[60vh] flex-col items-center justify-center font-mono">
      <div className="relative flex h-48 w-48 items-center justify-center">
        {/* SVG Circular Progress */}
        <svg
          className="absolute inset-0 h-full w-full -rotate-90 transform"
          viewBox="0 0 100 100"
        >
          {/* Background Track */}
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="transparent"
            stroke="var(--border)"
            strokeWidth="4"
          />
          {/* Progress Ring */}
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="transparent"
            stroke="var(--accent)"
            strokeWidth="4"
            strokeDasharray={`${2 * Math.PI * 40}`}
            strokeDashoffset={`${2 * Math.PI * 40 * (1 - progress / 100)}`}
            className="transition-all duration-500 ease-out"
          />
        </svg>
        {/* Center Text */}
        <div className="absolute flex flex-col items-center text-center">
          <span className="text-3xl font-bold text-white drop-shadow-[0_0_8px_var(--accent-glow)]">
            {Math.round(progress)}%
          </span>
          <span className="mt-1 text-[10px] uppercase tracking-widest text-[#2dd4bf] animate-pulse">
            Processing
          </span>
        </div>
      </div>

      <div className="mt-8 flex flex-col items-center gap-2 text-sm text-zinc-400">
        <p className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[color:var(--accent)] opacity-75"></span>
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[color:var(--accent)]"></span>
          </span>
          Executing Model Strategy...
        </p>
        <p className="text-xs font-mono text-zinc-500">Status: {status}</p>
      </div>
    </div>
  );
}
