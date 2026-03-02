import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-black/10 bg-[color:var(--surface)]/70 backdrop-blur supports-[backdrop-filter]:bg-[color:var(--surface)]/55">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
        <Link href="/" className="group flex items-baseline gap-2">
          <span className="font-display text-lg tracking-tight">
            First Claw Eater
          </span>
          <span className="rounded-full border border-black/10 bg-black/5 px-2 py-0.5 text-xs text-black/70 group-hover:bg-black/10">
            MVP
          </span>
        </Link>

        <nav className="flex items-center gap-3 text-sm">
          <Link
            href="/live"
            className="rounded-full border border-black/10 bg-white/40 px-3 py-1.5 text-black/80 hover:bg-white hover:text-black"
          >
            Live
          </Link>
          <Link
            href="/datasets"
            className="rounded-full px-3 py-1.5 text-black/80 hover:bg-black/5 hover:text-black"
          >
            Datasets
          </Link>
          <Link
            href="/prompt-templates"
            className="rounded-full px-3 py-1.5 text-black/80 hover:bg-black/5 hover:text-black"
          >
            Prompts
          </Link>
          <Link
            href="/runs"
            className="rounded-full bg-[color:var(--ink)] px-3 py-1.5 text-[color:var(--surface)] hover:bg-black"
          >
            Runs
          </Link>
        </nav>
      </div>
    </header>
  );
}
