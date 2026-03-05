"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import type { MeOut } from "@/app/lib/v4t";

function pageName(pathname: string): string {
  if (pathname === "/") return "Home";
  if (pathname === "/arena" || pathname.startsWith("/arena/")) return "Trials";
  if (pathname === "/leaderboard") return "Leaderboard";
  if (pathname === "/live") return "Live";
  if (pathname === "/contact") return "Contact";
  if (pathname === "/runs" || pathname.startsWith("/runs/")) return "Runs";
  if (pathname.startsWith("/admin")) return "Admin";
  return "Dashboard";
}

export function SiteHeader({ isHome }: { isHome?: boolean }) {
  const pathname = usePathname();
  const [me, setMe] = useState<MeOut | null>(null);

  useEffect(() => {
    fetch("/api/v4t/me")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => setMe(data as MeOut))
      .catch(() => setMe(null));
  }, []);

  return (
    <header className={`top-nav ${isHome ? "home-top-nav" : ""}`}>
      <div className="brand">
        <span className="brand-mark">V4T</span>
        <span className="brand-sub">Vibe4Trading / {pageName(pathname)}</span>
      </div>

      <nav className="nav-links">
        <Link href="/" className={pathname === "/" ? "active" : ""}>HOME</Link>
        <Link href="/arena" className={pathname === "/arena" || pathname.startsWith("/arena/") ? "active" : ""}>TRIALS</Link>
        <Link href="/leaderboard" className={pathname === "/leaderboard" ? "active" : ""}>LEADERBOARD</Link>
        <Link href="/live" className={pathname === "/live" ? "active" : ""}>LIVE</Link>
        <Link href="/contact" className={pathname === "/contact" ? "active" : ""}>CONTACT US</Link>
        {me?.is_admin && (
          <Link href="/admin/models" className={pathname.startsWith("/admin") ? "active" : ""}>ADMIN</Link>
        )}
      </nav>

      <div className="top-actions">
        {me?.quota && (
          <span className="user-chip">
            RUNS: {me.quota.runs_used}/{me.quota.runs_limit}
          </span>
        )}
        <span className="user-chip">USER: YOU</span>
        <Link href="/runs/new" className="new-run-btn">NEW RUN</Link>
        <Link href="#" className="waitlist">JOIN BETA</Link>
      </div>
    </header>
  );
}
