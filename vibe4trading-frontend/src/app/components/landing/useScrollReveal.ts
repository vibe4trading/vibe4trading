import { useEffect, useRef, useState } from "react";
import { isPrerendering } from "@/app/lib/prerender";

export function useScrollReveal(threshold = 0.15) {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(() => isPrerendering());

  useEffect(() => {
    if (isPrerendering()) return;

    const node = ref.current;
    if (!node || visible) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [threshold, visible]);

  return { ref, visible };
}
