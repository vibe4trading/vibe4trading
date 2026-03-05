"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import type { MeOut } from "@/app/lib/v4t";

const NAV_LINKS = [
  { href: "/live", label: "Live" },
  { href: "/arena", label: "Tournament" },
] as const;

export function SiteHeader() {
  const pathname = usePathname();
  const [me, setMe] = useState<MeOut | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    if (typeof window === "undefined") return "dark";
    const saved = localStorage.getItem("theme");
    return saved === "light" ? "light" : "dark";
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    fetch("/api/v4t/me")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => setMe(data as MeOut))
      .catch(() => setMe(null));
  }, []);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("theme", next);
    document.documentElement.setAttribute("data-theme", next);
  };

  const navLinkClass = (path: string) => {
    const isActive = pathname === path || (pathname.startsWith(path) && path !== "/");
    return `rounded-full px-3 py-1.5 transition-all duration-300 ${isActive
      ? "bg-white/10 text-white shadow-[0_0_15px_rgba(255,255,255,0.1)] border border-white/20"
      : "text-zinc-400 hover:bg-white/5 hover:text-white"
      }`;
  };

  const mobileNavLinkClass = (path: string) => {
    const isActive = pathname === path || (pathname.startsWith(path) && path !== "/");
    return `block rounded-xl px-4 py-3 text-sm font-medium transition-all ${isActive
      ? "bg-white/10 text-white border border-white/15"
      : "text-zinc-400 hover:bg-white/5 hover:text-white"
      }`;
  };

  return (
    <header className="sticky top-0 z-20 border-b border-[color:var(--border)] bg-[color:var(--bg)]/60 backdrop-blur-xl supports-[backdrop-filter]:bg-[color:var(--bg)]/60">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
        <Link href="/" className="group flex items-baseline gap-2">
          <span className="font-display text-xl tracking-tight text-white drop-shadow-[0_0_8px_var(--accent-glow)]">
            vibe4trading
          </span>
          <span className="rounded-full border border-[color:var(--accent)]/30 bg-[color:var(--accent)]/10 px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wider text-[color:var(--accent)] shadow-[0_0_10px_var(--accent-glow)]">
            MVP
          </span>
        </Link>

        <nav className="hidden items-center gap-3 text-sm font-medium md:flex">
          <button
            onClick={toggleTheme}
            className="rounded-full border border-zinc-700 bg-zinc-800/50 p-2 text-zinc-300 transition-colors hover:bg-zinc-700/50"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? "\u2600\uFE0F" : "\uD83C\uDF19"}
          </button>
          {me?.quota && (
            <div className="rounded-full border border-zinc-700 bg-zinc-800/50 px-3 py-1.5 text-xs text-zinc-300">
              Runs: {me.quota.runs_used}/{me.quota.runs_limit}
            </div>
          )}
          {me?.is_admin ? (
            <Link href="/admin/models" className={navLinkClass("/admin/models")}>
              Admin
            </Link>
          ) : null}
          {NAV_LINKS.map((link) => (
            <Link key={link.href} href={link.href} className={navLinkClass(link.href)}>
              {link.label}
            </Link>
          ))}
        </nav>

        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="flex items-center justify-center rounded-lg border border-white/10 bg-white/5 p-2 text-zinc-300 transition-colors hover:bg-white/10 md:hidden"
          aria-label="Toggle menu"
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </div>

        {mobileOpen && (
          <div className="animate-rise border-t border-white/5 bg-[color:var(--bg)]/95 px-5 pb-5 pt-3 backdrop-blur-xl md:hidden">
            <nav className="flex flex-col gap-1">
              {me?.is_admin ? (
                <Link
                  href="/admin/models"
                  className={mobileNavLinkClass("/admin/models")}
                  onClick={() => setMobileOpen(false)}
                >
                  Admin
                </Link>
              ) : null}
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={mobileNavLinkClass(link.href)}
                  onClick={() => setMobileOpen(false)}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          <div className="mt-4 flex items-center gap-3 border-t border-white/5 pt-4">
            <button
              onClick={toggleTheme}
              className="rounded-full border border-zinc-700 bg-zinc-800/50 p-2 text-zinc-300 transition-colors hover:bg-zinc-700/50"
              aria-label="Toggle theme"
            >
              {theme === "dark" ? "\u2600\uFE0F" : "\uD83C\uDF19"}
            </button>
            {me?.quota && (
              <div className="rounded-full border border-zinc-700 bg-zinc-800/50 px-3 py-1.5 text-xs text-zinc-300">
                Runs: {me.quota.runs_used}/{me.quota.runs_limit}
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
