"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type TypewriterProps = {
  text: string | string[];
  className?: string;
  typingSpeed?: number;
  deletingSpeed?: number;
  pauseDuration?: number;
  loop?: boolean;
  showCursor?: boolean;
  cursorCharacter?: string;
  startOnVisible?: boolean;
  onComplete?: () => void;
};

export function Typewriter({
  text,
  className = "",
  typingSpeed = 60,
  deletingSpeed = 40,
  pauseDuration = 1200,
  loop = false,
  showCursor = true,
  cursorCharacter = "_",
  startOnVisible = true,
  onComplete,
}: TypewriterProps) {
  const texts = useMemo(() => (Array.isArray(text) ? text : [text]), [text]);
  const containerRef = useRef<HTMLSpanElement | null>(null);
  const [started, setStarted] = useState(!startOnVisible);
  const [displayText, setDisplayText] = useState("");
  const [textIndex, setTextIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);
  const completedRef = useRef(false);

  useEffect(() => {
    if (!startOnVisible || started) return;
    const node = containerRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setStarted(true);
          observer.disconnect();
        }
      },
      { threshold: 0.3 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [startOnVisible, started]);

  useEffect(() => {
    if (!started || completedRef.current) return;

    const currentText = texts[textIndex];

    if (!isDeleting) {
      if (displayText.length < currentText.length) {
        const timeoutId = window.setTimeout(() => {
          setDisplayText(currentText.slice(0, displayText.length + 1));
        }, typingSpeed);
        return () => window.clearTimeout(timeoutId);
      }

      if (!loop && textIndex === texts.length - 1) {
        completedRef.current = true;
        onComplete?.();
        return;
      }

      const timeoutId = window.setTimeout(() => setIsDeleting(true), pauseDuration);
      return () => window.clearTimeout(timeoutId);
    }

    if (displayText.length > 0) {
      const timeoutId = window.setTimeout(() => {
        setDisplayText(displayText.slice(0, -1));
      }, deletingSpeed);
      return () => window.clearTimeout(timeoutId);
    }

    const timeoutId = window.setTimeout(() => {
      setIsDeleting(false);
      setTextIndex((current) => (current + 1) % texts.length);
    }, deletingSpeed);
    return () => window.clearTimeout(timeoutId);
  }, [
    started,
    displayText,
    deletingSpeed,
    isDeleting,
    loop,
    onComplete,
    pauseDuration,
    textIndex,
    texts,
    typingSpeed,
  ]);

  return (
    <span ref={containerRef} className={className}>
      {displayText}
      {showCursor ? <span className="animate-pulse">{cursorCharacter}</span> : null}
    </span>
  );
}
