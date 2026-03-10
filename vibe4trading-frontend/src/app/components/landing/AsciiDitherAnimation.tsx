import { useEffect, useRef } from "react";

type AsciiMount = HTMLDivElement & {
  __asciiDitherDestroy?: () => void;
};

export function AsciiDitherAnimation({ className }: { className?: string }) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
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

  return <div ref={hostRef} aria-hidden="true" className={className} />;
}
