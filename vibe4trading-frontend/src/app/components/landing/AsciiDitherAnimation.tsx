import { useEffect, useRef } from "react";
import { isPrerendering } from "@/app/lib/prerender";

type AsciiMount = HTMLDivElement & {
  __asciiDitherDestroy?: () => void;
};

export function AsciiDitherAnimation({ className }: { className?: string }) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isPrerendering()) return;

    const host = hostRef.current;
    if (!host) return;

    host.style.position = "absolute";
    host.style.inset = "0";
    host.style.top = "0";
    host.style.left = "0";
    host.style.right = "0";
    host.style.bottom = "0";
    host.style.height = "100%";
    host.style.zIndex = "0";
    host.style.pointerEvents = "none";
    host.style.overflow = "hidden";

    host.innerHTML =
      '<div data-ascii-dither-bg aria-hidden="true" style="position:absolute;inset:0;height:100%;z-index:0;pointer-events:none;overflow:hidden"></div>';

    const script = document.createElement("script");
    script.src = "/animation.js";
    script.async = true;
    host.appendChild(script);

    return () => {
      const mount = host.querySelector("[data-ascii-dither-bg]") as AsciiMount | null;
      mount?.__asciiDitherDestroy?.();
      script.remove();
      host.innerHTML = "";
    };
  }, []);

  if (isPrerendering()) {
    return (
      <div
        className={className}
        style={{
          position: "absolute",
          inset: 0,
          height: "100%",
          zIndex: 0,
          pointerEvents: "none",
          overflow: "hidden",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <p
          data-prerender-fallback
          style={{
            fontFamily: "monospace",
            fontSize: "0.75rem",
            lineHeight: 1.4,
            color: "rgba(255, 255, 255, 0.08)",
            textAlign: "center",
            whiteSpace: "pre-line",
            maxWidth: "80ch",
          }}
        >
          {`Vibe4Trading — LLM-native crypto strategy benchmarking.
Test AI trading strategies across repeatable historical market regimes.
Benchmark Lab · Strategy Arena · Leaderboard`}
        </p>
      </div>
    );
  }

  return <div ref={hostRef} aria-hidden="true" className={className} />;
}
