/**
 * Detects if the page is being rendered by a headless prerender service
 * (e.g. prerender/prerender running Headless Chrome).
 *
 * Used to skip DOM-mutating features (product tours, onboarding overlays)
 * that would otherwise be baked into the static HTML served to search
 * engines and social media crawlers.
 */
export function isPrerendering(): boolean {
  if (typeof navigator === "undefined") return true;
  return /HeadlessChrome/i.test(navigator.userAgent);
}
