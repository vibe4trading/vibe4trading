type NewRunFooterProps = {
  onMyRuns: () => void;
  onNewRun: () => void;
  disabled?: boolean;
};

export function NewRunFooter({ onMyRuns, onNewRun, disabled }: NewRunFooterProps) {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-30 flex justify-center px-5 pb-5">
      <div className="pointer-events-auto w-full max-w-3xl">
        <div className="group relative overflow-hidden rounded-2xl border border-white/10 bg-black/40 shadow-[0_12px_40px_rgba(0,0,0,0.35)] backdrop-blur-xl transition-all duration-300 hover:-translate-y-0.5 hover:border-white/20 hover:bg-black/45">
          <div className="absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
            <div className="absolute -left-24 -top-24 h-56 w-56 rounded-full bg-[color:var(--accent)]/16 blur-3xl" />
            <div className="absolute -right-24 -bottom-24 h-56 w-56 rounded-full bg-[color:var(--accent-2)]/16 blur-3xl" />
          </div>

          <div className="relative flex items-center justify-between gap-3 p-4">
            <button
              type="button"
              onClick={onMyRuns}
              className="inline-flex items-center justify-center gap-2 rounded-full border border-white/15 bg-white/5 px-7 py-3 text-sm font-semibold text-white transition-all hover:bg-white/10 hover:border-white/25 hover:shadow-[0_0_15px_rgba(255,255,255,0.1)]"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              My Runs
            </button>

            <button
              type="button"
              onClick={onNewRun}
              disabled={disabled}
              className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-7 py-3 text-sm font-bold text-black transition-all hover:bg-zinc-200 hover:shadow-[0_0_22px_rgba(255,255,255,0.22)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              New Run
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
