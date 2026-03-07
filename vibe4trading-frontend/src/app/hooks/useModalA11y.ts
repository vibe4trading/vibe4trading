import { useEffect, useRef } from "react";

export function useModalA11y(
  isOpen: boolean,
  onClose: () => void,
  options?: {
    closeOnEscape?: boolean;
    restoreFocus?: boolean;
    lockBodyScroll?: boolean;
  }
) {
  const {
    closeOnEscape = true,
    restoreFocus = true,
    lockBodyScroll = true,
  } = options ?? {};

  const panelRef = useRef<HTMLElement | null>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    if (restoreFocus) {
      previouslyFocused.current = document.activeElement as HTMLElement | null;
    }

    if (lockBodyScroll) {
      document.body.style.overflow = "hidden";
    }

    const onKeyDown = (e: KeyboardEvent) => {
      if (closeOnEscape && e.key === "Escape") {
        onClose();
        return;
      }

      if (e.key === "Tab") {
        const panel = panelRef.current;
        if (!panel) return;

        const focusables = Array.from(
          panel.querySelectorAll<HTMLElement>(
            'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])'
          )
        ).filter((el) => !el.hasAttribute("disabled") && el.tabIndex !== -1);

        if (focusables.length === 0) return;

        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement as HTMLElement | null;

        if (e.shiftKey) {
          if (!active || active === first || !panel.contains(active)) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (active === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
      if (lockBodyScroll) {
        document.body.style.overflow = "";
      }
      if (restoreFocus) {
        previouslyFocused.current?.focus?.();
      }
    };
  }, [isOpen, onClose, closeOnEscape, restoreFocus, lockBodyScroll]);

  return { panelRef };
}
