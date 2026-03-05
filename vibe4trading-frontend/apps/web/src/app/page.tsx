import Link from "next/link";

export default function Home() {
  return (
    <div className="animate-rise">
      <div className="flex flex-col gap-10">
        <section className="relative overflow-hidden rounded-3xl border border-[color:var(--border)] bg-[color:var(--surface)] p-10 shadow-[var(--shadow)] backdrop-blur-sm">
          <div className="absolute inset-0 opacity-[0.4] [mask-image:radial-gradient(circle_at_20%_10%,black,transparent_60%)]">
            <div className="absolute -left-20 -top-16 h-72 w-72 rounded-full bg-[radial-gradient(circle_at_center,var(--accent-2)_0%,transparent_60%)] blur-2xl mix-blend-screen" />
            <div className="absolute right-10 top-16 h-80 w-80 rounded-full bg-[radial-gradient(circle_at_center,var(--accent)_0%,transparent_60%)] blur-2xl mix-blend-screen" />
          </div>

          <div className="relative z-10">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 mb-6">
              <span className="flex h-2 w-2 rounded-full bg-[color:var(--accent)] shadow-[0_0_8px_var(--accent)]" />
              <p className="text-xs font-semibold tracking-widest text-zinc-300">
                LLM TRADING BENCHMARKS
              </p>
            </div>

             <h1 className="font-display text-5xl leading-[1.05] tracking-tight text-white sm:text-6xl drop-shadow-md">
               Make models sweat<br />on the same window.
             </h1>
             <p className="mt-5 max-w-2xl text-lg leading-relaxed text-zinc-400">
              Inject market + sentiment windows via the API, run a replay, inspect the equity curve, and read
              every decision (accepted or rejected) with full prompt/response audit.
             </p>

             <div className="mt-8 flex flex-col gap-4 sm:flex-row">
               <Link
                href="/arena"
                 className="group relative inline-flex items-center justify-center rounded-full bg-white px-8 py-3.5 text-sm font-semibold text-black transition-all hover:bg-zinc-200 hover:shadow-[0_0_30px_rgba(255,255,255,0.3)]"
               >
                 Open Tournament
               </Link>
               <Link
                 href="/live"
                 className="group inline-flex items-center justify-center rounded-full border border-white/20 bg-white/5 px-8 py-3.5 text-sm font-medium text-white transition-all hover:bg-white/10 hover:border-white/30"
               >
                 Live Dashboard
               </Link>
             </div>
           </div>
         </section>

        <section className="animate-rise-1 grid gap-6 md:grid-cols-2">
          <Link
            href="/live"
            className="group relative overflow-hidden rounded-2xl border border-[color:var(--border)] bg-white/5 p-6 shadow-lg transition-all hover:-translate-y-1 hover:border-[color:var(--accent)]/50 hover:bg-white/10 hover:shadow-[0_8px_30px_var(--accent-glow)]"
          >
            <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-[color:var(--accent)]/10 blur-2xl transition-all group-hover:bg-[color:var(--accent)]/20" />
            <div className="text-xs font-bold tracking-widest text-[color:var(--accent)]">
              LIVE
            </div>
            <div className="mt-3 font-display text-2xl tracking-tight text-white">
              Dashboard
            </div>
            <p className="mt-3 text-sm leading-relaxed text-zinc-400">
              Start a live run and watch decisions stream in.
            </p>
          </Link>

          <Link
            href="/arena"
            className="group relative overflow-hidden rounded-2xl border border-[color:var(--border)] bg-white/5 p-6 shadow-lg transition-all hover:-translate-y-1 hover:border-[color:var(--accent-2)]/50 hover:bg-white/10 hover:shadow-[0_8px_30px_var(--accent-2-glow)]"
          >
            <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-[color:var(--accent-2)]/10 blur-2xl transition-all group-hover:bg-[color:var(--accent-2)]/20" />
            <div className="text-xs font-bold tracking-widest text-[color:var(--accent-2)]">
              COMPETE
            </div>
            <div className="mt-3 font-display text-2xl tracking-tight text-white">
              Tournament
            </div>
            <p className="mt-3 text-sm leading-relaxed text-zinc-400">
              Submit prompts to tournament scenarios and rank by compounded return.
            </p>
          </Link>
        </section>
      </div>
    </div>
  );
}
