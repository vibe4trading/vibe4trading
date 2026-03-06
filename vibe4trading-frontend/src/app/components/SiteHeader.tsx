"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type FocusEvent, useCallback, useEffect, useRef, useState } from "react";
import { useSession, signIn, signOut } from "next-auth/react";

import { useNewRunModal } from "@/app/components/NewRunProvider";
import { apiJson, type MeApiTokenOut, type MeOut } from "@/app/lib/v4t";

type TokenStatus =
  | { tone: "idle"; message: string }
  | { tone: "loading"; message: string }
  | { tone: "success"; message: string }
  | { tone: "error"; message: string };

async function copyText(value: string) {
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const input = document.createElement("textarea");
  input.value = value;
  input.setAttribute("readonly", "true");
  input.style.position = "absolute";
  input.style.left = "-9999px";
  document.body.appendChild(input);
  input.select();
  document.execCommand("copy");
  document.body.removeChild(input);
}

export function SiteHeader({ isHome }: { isHome?: boolean }) {
  const pathname = usePathname();
  const { data: session, status } = useSession();
  const [meData, setMeData] = useState<MeOut | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [loginPending, setLoginPending] = useState(false);
  const profileCloseTimerRef = useRef<number | null>(null);
  const [tokenStatus, setTokenStatus] = useState<TokenStatus>({
    tone: "idle",
    message: "Copy your bot token only when you need to wire up automation.",
  });
  const { openNewRun } = useNewRunModal();

  useEffect(() => {
    if (status === "authenticated") {
      apiJson<MeOut>("/me")
        .then((data) => setMeData(data))
        .catch(() => setMeData(null));
    }
  }, [status]);

  useEffect(() => {
    if (tokenStatus.tone !== "success") return;

    const timeoutId = window.setTimeout(() => {
      setTokenStatus({
        tone: "idle",
        message: "Copy your bot token only when you need to wire up automation.",
      });
    }, 2400);

    return () => window.clearTimeout(timeoutId);
  }, [tokenStatus]);

  useEffect(() => {
    return () => {
      if (profileCloseTimerRef.current !== null) {
        window.clearTimeout(profileCloseTimerRef.current);
      }
    };
  }, []);

  const me = status === "authenticated" ? meData : null;

  const profileName = me?.display_name ?? session?.user?.name ?? session?.user?.email ?? "YOU";
  const profileEmail = me?.email ?? session?.user?.email ?? null;

  const profileInitial = profileName.trim().charAt(0).toUpperCase() || "U";
  const profileTriggerClassName = isHome
    ? "flex h-11 w-11 items-center justify-center rounded-full border-2 border-white/35 bg-white/8 text-white transition hover:bg-white/16 focus-visible:bg-white/16 focus-visible:outline-none"
    : "flex h-11 w-11 items-center justify-center rounded-full border-2 border-[#555] bg-[#f0f0f0] text-[#262626] transition hover:bg-[#e1e8f8] focus-visible:bg-[#e1e8f8] focus-visible:outline-none";
  const profileMenuClassName = isHome
    ? "absolute left-0 top-[calc(100%+4px)] z-30 w-[min(360px,calc(100vw-44px))] border-2 border-[#485169] bg-[linear-gradient(180deg,rgba(12,16,24,0.98)_0%,rgba(6,8,12,0.98)_100%)] p-4 text-white shadow-[0_22px_44px_rgba(0,0,0,0.42)] transition [@media(min-width:640px)]:left-auto [@media(min-width:640px)]:right-0"
    : "absolute left-0 top-[calc(100%+4px)] z-30 w-[min(360px,calc(100vw-44px))] border-2 border-[#2f2f2f] bg-[linear-gradient(180deg,#f8f8f8_0%,#efefef_100%)] p-4 text-[#171717] shadow-[0_18px_34px_rgba(0,0,0,0.22)] transition [@media(min-width:640px)]:left-auto [@media(min-width:640px)]:right-0";
  const profileSubtleTextClassName = isHome ? "text-[#bfc8db]" : "text-[#575757]";
  const profileMetricClassName = isHome
    ? "grid gap-2 border-2 border-[#56627f] bg-white/8 p-3"
    : "grid gap-2 border-2 border-[#505050] bg-white/70 p-3";
  const profileActionClassName = isHome
    ? "border-2 border-[#56627f] bg-white/8 px-3 py-2 text-sm leading-none text-white transition hover:bg-white/14 focus-visible:bg-white/14 focus-visible:outline-none"
    : "border-2 border-[#303030] bg-[#f4f4f4] px-3 py-2 text-sm leading-none text-[#171717] transition hover:bg-[#e7e7e7] focus-visible:bg-[#e7e7e7] focus-visible:outline-none";
  const profilePrimaryActionClassName = isHome
    ? "border-2 border-[#c6d7ff] bg-[#dfe8ff] px-3 py-2 text-sm leading-none text-[#111a2e] transition hover:bg-[#c6d7ff] focus-visible:bg-[#c6d7ff] focus-visible:outline-none"
    : "border-2 border-[#355096] bg-[#dce8fd] px-3 py-2 text-sm leading-none text-[#16234a] transition hover:bg-[#cbdcff] focus-visible:bg-[#cbdcff] focus-visible:outline-none";

  function clearProfileCloseTimer() {
    if (profileCloseTimerRef.current !== null) {
      window.clearTimeout(profileCloseTimerRef.current);
      profileCloseTimerRef.current = null;
    }
  }

  function openProfileMenu() {
    clearProfileCloseTimer();
    setProfileOpen(true);
  }

  function scheduleProfileClose() {
    clearProfileCloseTimer();
    profileCloseTimerRef.current = window.setTimeout(() => {
      setProfileOpen(false);
      profileCloseTimerRef.current = null;
    }, 180);
  }

  function closeProfileOnBlur(event: FocusEvent<HTMLDivElement>) {
    clearProfileCloseTimer();
    if (!event.currentTarget.contains(event.relatedTarget)) {
      setProfileOpen(false);
    }
  }

  const onCopyToken = useCallback(async () => {
    setTokenStatus({ tone: "loading", message: "Requesting your bot token..." });
    try {
      const token = await apiJson<MeApiTokenOut>("/me/api-token");
      await copyText(token.api_token);
      setMeData((current) => (current ? { ...current, has_api_token: true } : current));
      setTokenStatus({
        tone: "success",
        message: token.created ? "New bot token issued and copied." : "Bot token copied.",
      });
    } catch (error) {
      setTokenStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Unable to copy bot token.",
      });
    }
  }, []);

  return (
    <header className={`top-nav ${isHome ? "home-top-nav" : ""}`}>
      <div className="brand">
        <span className="brand-mark">V4T</span>
        <span className="brand-sub">Vibe4Trading</span>
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
        {status === "authenticated" && me?.quota && (
          <span className="user-chip">
            TODAY: {me.quota.runs_used}/{me.quota.runs_limit}
          </span>
        )}
        {status === "authenticated" ? (
          <>
            <button type="button" className="new-run-btn" onClick={openNewRun}>NEW RUN</button>
            <div
              className="relative"
              onMouseEnter={openProfileMenu}
              onMouseLeave={scheduleProfileClose}
              onBlur={closeProfileOnBlur}
            >
              <button
                type="button"
                className={profileTriggerClassName}
                aria-haspopup="menu"
                aria-expanded={profileOpen}
                onClick={() => {
                  clearProfileCloseTimer();
                  setProfileOpen((value) => !value);
                }}
                onFocus={openProfileMenu}
              >
                <span className="sr-only">Open profile menu</span>
                <span
                  className={isHome
                    ? "grid h-7 w-7 place-items-center rounded-full border border-white/20 bg-white/8"
                    : "grid h-7 w-7 place-items-center rounded-full border border-current bg-white/50"}
                  aria-hidden="true"
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" focusable="false">
                    <path d="M12 12.35a4.1 4.1 0 1 0-4.1-4.1 4.1 4.1 0 0 0 4.1 4.1Zm0 2.05c-3.75 0-6.8 2.08-6.8 4.65V21h13.6v-1.95c0-2.57-3.05-4.65-6.8-4.65Z" />
                  </svg>
                </span>
              </button>

              <div
                className={`${profileMenuClassName} ${profileOpen ? "pointer-events-auto translate-y-0 opacity-100" : "pointer-events-none -translate-y-1 opacity-0"}`}
                role="menu"
              >
                <div className="flex items-start justify-between gap-3 border-b border-black/15 pb-3 [@media(min-width:640px)]:border-b" >
                  <div>
                    <p className={`mb-1 text-[10px] leading-none tracking-[0.22em] ${profileSubtleTextClassName}`}>ACTIVE PILOT</p>
                    <strong className="block text-[28px] leading-none">{profileName}</strong>
                    <p className={`mt-2 text-sm ${profileSubtleTextClassName}`}>{profileEmail ?? "Signed in with V4T SSO"}</p>
                  </div>
                  <span
                    className={isHome
                      ? "grid h-9 w-9 place-items-center rounded-full border border-white/25 bg-white/8 text-sm"
                      : "grid h-9 w-9 place-items-center rounded-full border-2 border-[#355096] bg-[#dce7ff] text-sm text-[#1f3773]"}
                  >
                    {profileInitial}
                  </span>
                </div>

                <div className="mt-3">
                  <div className={profileMetricClassName}>
                    <span className={`text-[11px] leading-none tracking-[0.18em] ${profileSubtleTextClassName}`}>DAILY QUOTA</span>
                    <strong className="text-2xl leading-none">
                      {me?.quota ? `${me.quota.runs_used}/${me.quota.runs_limit}` : "--"}
                    </strong>
                  </div>
                </div>

                <p className={`mt-3 text-sm leading-6 ${profileSubtleTextClassName}`}>
                  Daily run quota resets at 00:00 UTC. Bot token access is for automation only and is fetched on demand.
                </p>

                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className={profilePrimaryActionClassName}
                    onClick={onCopyToken}
                    disabled={tokenStatus.tone === "loading"}
                  >
                    {tokenStatus.tone === "loading" ? "COPYING..." : "COPY BOT TOKEN"}
                  </button>
                  <button
                    type="button"
                    className={profileActionClassName}
                    onClick={() => signOut()}
                  >
                    LOGOUT
                  </button>
                </div>

                <p
                  className={`mt-3 text-[13px] ${
                    tokenStatus.tone === "loading"
                      ? "text-[#465f9e]"
                      : tokenStatus.tone === "success"
                        ? "text-[#1f7a4c]"
                        : tokenStatus.tone === "error"
                          ? "text-[#ac3838]"
                          : profileSubtleTextClassName
                  }`}
                >
                  {tokenStatus.message}
                </p>
              </div>
            </div>
          </>
        ) : status === "unauthenticated" ? (
          <button
            type="button"
            className={`waitlist${loginPending ? " waitlist-pending" : ""}`}
            disabled={loginPending}
            onClick={() => { setLoginPending(true); signIn("v4t"); }}
          >
            {loginPending && <span className="waitlist-spinner" aria-hidden="true" />}
            {loginPending ? "SIGNING IN…" : "LOGIN"}
          </button>
        ) : null}
      </div>
    </header>
  );
}
