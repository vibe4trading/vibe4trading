import { useCallback, useRef, useState, type FocusEvent } from "react";
import { useTourContext } from "@/app/components/TourProvider";

const TOURS = [
  { id: "trials-v1", label: "Trials Tour" },
  { id: "leaderboard-v1", label: "Leaderboard Tour" },
  { id: "arena-submission-v1", label: "Arena Submission Tour" },
] as const;

interface TourButtonProps {
  isHome?: boolean;
}

export default function TourButton({ isHome = false }: TourButtonProps) {
  const { startTour } = useTourContext();
  const [menuOpen, setMenuOpen] = useState(false);
  const closeTimerRef = useRef<number | null>(null);

  function clearCloseTimer() {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }

  function openMenu() {
    clearCloseTimer();
    setMenuOpen(true);
  }

  function scheduleClose() {
    clearCloseTimer();
    closeTimerRef.current = window.setTimeout(() => {
      setMenuOpen(false);
      closeTimerRef.current = null;
    }, 180);
  }

  function closeOnBlur(event: FocusEvent<HTMLDivElement>) {
    clearCloseTimer();
    if (!event.currentTarget.contains(event.relatedTarget)) {
      setMenuOpen(false);
    }
  }

  const handleSelect = useCallback(
    (tourId: string) => {
      setMenuOpen(false);
      startTour(tourId);
    },
    [startTour],
  );

  const triggerClassName = isHome
    ? "flex h-11 w-11 items-center justify-center rounded-full border-2 border-white/35 bg-white/8 text-white transition hover:bg-white/16 focus-visible:bg-white/16 focus-visible:outline-none"
    : "flex h-11 w-11 items-center justify-center rounded-full border-2 border-[#555] bg-[#f0f0f0] text-[#262626] transition hover:bg-[#e1e8f8] focus-visible:bg-[#e1e8f8] focus-visible:outline-none";

  const menuClassName = isHome
    ? "absolute right-0 top-[calc(100%+4px)] z-30 w-56 border-2 border-[#485169] bg-[linear-gradient(180deg,rgba(12,16,24,0.98)_0%,rgba(6,8,12,0.98)_100%)] p-2 text-white shadow-[0_22px_44px_rgba(0,0,0,0.42)] transition"
    : "absolute right-0 top-[calc(100%+4px)] z-30 w-56 border-2 border-[#2f2f2f] bg-[linear-gradient(180deg,#f8f8f8_0%,#efefef_100%)] p-2 text-[#171717] shadow-[0_18px_34px_rgba(0,0,0,0.22)] transition";

  const itemClassName = isHome
    ? "w-full px-3 py-2 text-left text-sm leading-none text-white transition hover:bg-white/14 focus-visible:bg-white/14 focus-visible:outline-none"
    : "w-full px-3 py-2 text-left text-sm leading-none text-[#171717] transition hover:bg-[#e7e7e7] focus-visible:bg-[#e7e7e7] focus-visible:outline-none";

  return (
    <div
      className="relative"
      onMouseEnter={openMenu}
      onMouseLeave={scheduleClose}
      onBlur={closeOnBlur}
    >
      <button
        type="button"
        className={triggerClassName}
        aria-haspopup="menu"
        aria-expanded={menuOpen}
        onClick={() => {
          clearCloseTimer();
          setMenuOpen((v) => !v);
        }}
        onFocus={openMenu}
      >
        <span className="sr-only">Open guided tours</span>
        <span className="text-lg font-bold leading-none" aria-hidden="true">
          ?
        </span>
      </button>

      <div
        className={`${menuClassName} ${menuOpen ? "pointer-events-auto translate-y-0 opacity-100" : "pointer-events-none -translate-y-1 opacity-0"}`}
        role="menu"
      >
        {TOURS.map((tour) => (
          <button
            key={tour.id}
            type="button"
            role="menuitem"
            className={itemClassName}
            onClick={() => handleSelect(tour.id)}
          >
            {tour.label}
          </button>
        ))}
      </div>
    </div>
  );
}
