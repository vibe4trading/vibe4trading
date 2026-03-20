import { Link } from "react-router-dom";
import { useLocation } from "react-router-dom";
import { type FocusEvent, useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/auth";

import { useNewRunModal } from "@/app/components/NewRunProvider";
import TourButton from "@/app/components/TourButton";
import { LanguageSwitcher } from "@/app/components/LanguageSwitcher";
import { WalletAuthButton } from "@/app/components/WalletAuthButton";
import { apiJson, type MeApiTokenOut } from "@/app/lib/v4t";

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
  const { t } = useTranslation("common");
  const { pathname } = useLocation();
  const { status, user, signIn, signOut } = useAuth();
  const [profileOpen, setProfileOpen] = useState(false);
  const [loginPending, setLoginPending] = useState(false);
  const profileCloseTimerRef = useRef<number | null>(null);
  const [tokenStatus, setTokenStatus] = useState<TokenStatus>({
    tone: "idle",
    message: t("profile.tokenIdle"),
  });
  const { openNewRun } = useNewRunModal();

  useEffect(() => {
    if (tokenStatus.tone !== "success") return;

    const timeoutId = window.setTimeout(() => {
      setTokenStatus({
        tone: "idle",
        message: t("profile.tokenIdle"),
      });
    }, 2400);

    return () => window.clearTimeout(timeoutId);
  }, [tokenStatus, t]);

  useEffect(() => {
    return () => {
      if (profileCloseTimerRef.current !== null) {
        window.clearTimeout(profileCloseTimerRef.current);
      }
    };
  }, []);

  const me = user;

  const profileName = user?.display_name ?? user?.email ?? "YOU";
  const profileEmail = user?.email ?? null;

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
    setTokenStatus({ tone: "loading", message: t("profile.tokenLoading") });
    try {
      const token = await apiJson<MeApiTokenOut>("/me/api-token");
      await copyText(token.api_token);
      setTokenStatus({
        tone: "success",
        message: token.created ? t("profile.tokenSuccessNew") : t("profile.tokenSuccess"),
      });
    } catch (error) {
      setTokenStatus({
        tone: "error",
        message: error instanceof Error ? error.message : t("profile.tokenError"),
      });
    }
  }, [t]);

  return (
    <header className={`top-nav ${isHome ? "home-top-nav" : ""}`}>
      <div className="brand">
        <span className="brand-mark">V4T</span>
        <span className="brand-sub">Vibe4Trading</span>
      </div>

      <nav className="nav-links">
        <Link to="/" className={pathname === "/" ? "active" : ""}>{t("nav.home")}</Link>
        <Link to="/arena" className={pathname === "/arena" || pathname.startsWith("/arena/") ? "active" : ""}>{t("nav.trials")}</Link>
        <Link to="/leaderboard" data-tour="trials-leaderboard-link" className={pathname === "/leaderboard" ? "active" : ""}>{t("nav.leaderboard")}</Link>
        <Link to="/live" className={pathname === "/live" ? "active" : ""}>{t("nav.live")}</Link>
        <Link to="/contact" className={pathname === "/contact" ? "active" : ""}>{t("nav.contact")}</Link>
        {me?.is_admin && (
          <Link to="/admin/models" className={pathname.startsWith("/admin") ? "active" : ""}>{t("nav.admin")}</Link>
        )}
      </nav>

      <div className="top-actions">
        <TourButton isHome={isHome} />
        <LanguageSwitcher isHome={isHome} />
        {status === "authenticated" && me?.quota && (
          <span className="user-chip" data-tour="trials-quota-chip">
            {t("nav.today", { current: me.quota.runs_used, total: me.quota.runs_limit })}
          </span>
        )}
        {status === "authenticated" ? (
          <>
            <button type="button" className="new-run-btn" onClick={openNewRun}>{t("nav.newRun")}</button>
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
                <span className="sr-only">{t("profile.openMenu")}</span>
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
                    <p className={`mb-1 text-[10px] leading-none tracking-[0.22em] ${profileSubtleTextClassName}`}>{t("profile.activePilot")}</p>
                    <strong className="block text-[28px] leading-none">{profileName}</strong>
                    <p className={`mt-2 text-sm ${profileSubtleTextClassName}`}>{profileEmail ?? t("profile.signedInSSO")}</p>
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
                    <span className={`text-[11px] leading-none tracking-[0.18em] ${profileSubtleTextClassName}`}>{t("profile.dailyQuota")}</span>
                    <strong className="text-2xl leading-none">
                      {me?.quota ? `${me.quota.runs_used}/${me.quota.runs_limit}` : "--"}
                    </strong>
                  </div>
                </div>

                <p className={`mt-3 text-sm leading-6 ${profileSubtleTextClassName}`}>
                  {t("profile.quotaInfo")}
                </p>

                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className={profilePrimaryActionClassName}
                    onClick={onCopyToken}
                    disabled={tokenStatus.tone === "loading"}
                  >
                    {tokenStatus.tone === "loading" ? t("profile.copying") : t("profile.copyBotToken")}
                  </button>
                  <button
                    type="button"
                    className={profileActionClassName}
                    onClick={() => signOut()}
                  >
                    {t("nav.logout")}
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
          <div className="flex gap-2">
            <button
              type="button"
              className={`waitlist${loginPending ? " waitlist-pending" : ""}`}
              disabled={loginPending}
              onClick={() => { setLoginPending(true); signIn(pathname); }}
            >
              {loginPending && <span className="waitlist-spinner" aria-hidden="true" />}
              {loginPending ? t("nav.signingIn") : t("nav.login")}
            </button>
            <WalletAuthButton />
          </div>
        ) : null}
      </div>
    </header>
  );
}
