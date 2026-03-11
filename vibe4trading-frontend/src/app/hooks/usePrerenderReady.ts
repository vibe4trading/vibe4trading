import { useEffect, useRef } from "react";

/**
 * Signals prerender readiness via `window.prerenderReady`.
 *
 * For static pages, pass `true` directly to signal immediately.
 * For data-fetching pages, pass a boolean that becomes `true`
 * once the meaningful initial load has completed.
 *
 * Once signalled, the flag stays `true` for the lifetime of the page.
 */
export function usePrerenderReady(isReady: boolean): void {
  const signalled = useRef(false);

  useEffect(() => {
    if (isReady && !signalled.current) {
      signalled.current = true;
      window.prerenderReady = true;
    }
  }, [isReady]);
}
