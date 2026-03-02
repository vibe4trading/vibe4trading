import Link from "next/link";

export default function Home() {
  return (
    <div className="animate-rise">
      <div className="flex flex-col gap-8">
        <section className="relative overflow-hidden rounded-3xl border border-black/10 bg-[color:var(--surface)] p-8 shadow-[var(--shadow)]">
          <div className="absolute inset-0 opacity-[0.65] [mask-image:radial-gradient(circle_at_20%_10%,black,transparent_60%)]">
            <div className="absolute -left-20 -top-16 h-56 w-56 rounded-full bg-[radial-gradient(circle_at_center,rgba(20,184,166,0.35),transparent_60%)]" />
            <div className="absolute right-10 top-16 h-64 w-64 rounded-full bg-[radial-gradient(circle_at_center,rgba(249,115,22,0.28),transparent_60%)]" />
          </div>

          <div className="relative">
            <p className="text-xs font-medium tracking-widest text-black/55">
              LLM TRADING BENCHMARKS • PAPER SIM • REPLAYABLE
            </p>
            <h1 className="mt-3 font-display text-4xl leading-[1.05] tracking-tight sm:text-5xl">
              Make models sweat on the same market window.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-black/70">
              Import a dataset, run a replay, inspect the equity curve, and read
              every decision (accepted or rejected) with full prompt/response audit.
            </p>

            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/runs"
                className="inline-flex items-center justify-center rounded-full bg-[color:var(--ink)] px-5 py-2.5 text-sm font-medium text-[color:var(--surface)] hover:bg-black"
              >
                Open Runs
              </Link>
              <Link
                href="/datasets"
                className="inline-flex items-center justify-center rounded-full border border-black/15 bg-white/50 px-5 py-2.5 text-sm font-medium text-black/85 hover:bg-white"
              >
                Import Dataset
              </Link>
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <Link
            href="/datasets"
            className="group rounded-2xl border border-black/10 bg-white/60 p-5 shadow-[var(--shadow)] transition hover:-translate-y-0.5 hover:bg-white"
          >
            <div className="text-xs font-medium tracking-widest text-black/50">
              STEP 1
            </div>
            <div className="mt-2 font-display text-xl tracking-tight">
              Datasets
            </div>
            <p className="mt-2 text-sm leading-6 text-black/65">
              Create/import spot + sentiment windows. Demo, empty, or seeded DexScreener.
            </p>
          </Link>

          <Link
            href="/prompt-templates"
            className="group rounded-2xl border border-black/10 bg-white/60 p-5 shadow-[var(--shadow)] transition hover:-translate-y-0.5 hover:bg-white"
          >
            <div className="text-xs font-medium tracking-widest text-black/50">
              STEP 2
            </div>
            <div className="mt-2 font-display text-xl tracking-tight">
              Prompts
            </div>
            <p className="mt-2 text-sm leading-6 text-black/65">
              Mustache templates with variables, snapshotted into each run config.
            </p>
          </Link>

          <Link
            href="/runs"
            className="group rounded-2xl border border-black/10 bg-white/60 p-5 shadow-[var(--shadow)] transition hover:-translate-y-0.5 hover:bg-white"
          >
            <div className="text-xs font-medium tracking-widest text-black/50">
              STEP 3
            </div>
            <div className="mt-2 font-display text-xl tracking-tight">
              Runs
            </div>
            <p className="mt-2 text-sm leading-6 text-black/65">
              Execute replays via the job worker, then inspect timeline + decisions.
            </p>
          </Link>
        </section>
      </div>
    </div>
  );
}
