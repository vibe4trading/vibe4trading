import { useEffect, useRef } from "react";

const CHARSET = " .:-=+*#%@";
const CELL_SIZE = 12;
const MAX_FPS = 24;

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function sampleField(x: number, y: number, time: number) {
  const radius = Math.sqrt(x * x + y * y);
  const angle = Math.atan2(y, x);
  const waveA = Math.sin((x * 3.4 + time * 0.9) * 1.15);
  const waveB = Math.cos((y * 4.8 - time * 0.75) * 0.95);
  const rings = Math.sin(radius * 15 - time * 1.9 + angle * 3.2);
  const grain = Math.sin((x * 18.2 + y * 12.7) + time * 3.1);
  return (waveA * 0.3 + waveB * 0.24 + rings * 0.34 + grain * 0.12 + 1) * 0.5;
}

export function AsciiDitherAnimation({ className }: { className?: string }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const mount = mountRef.current;
    const canvas = canvasRef.current;
    if (!mount || !canvas) return;

    const context = canvas.getContext("2d");
    if (!context) return;

    let frameId = 0;
    let lastFrame = 0;
    let width = 0;
    let height = 0;
    let cols = 0;
    let rows = 0;
    let dpr = 1;
    let isDisposed = false;
    let fadeInQueued = false;
    const pointer = { active: false, x: 0.5, y: 0.5, pulse: 0 };

    const setCanvasSize = () => {
      const rect = mount.getBoundingClientRect();
      width = Math.max(1, Math.round(rect.width));
      height = Math.max(1, Math.round(rect.height));
      dpr = Math.min(window.devicePixelRatio || 1, 2);

      canvas.width = Math.max(1, Math.round(width * dpr));
      canvas.height = Math.max(1, Math.round(height * dpr));
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      context.setTransform(1, 0, 0, 1, 0, 0);
      context.scale(dpr, dpr);
      context.textBaseline = "middle";
      context.textAlign = "center";
      context.font = `600 ${CELL_SIZE}px "Helvetica Neue", Helvetica, Arial, sans-serif`;
      cols = Math.max(28, Math.floor(width / (CELL_SIZE * 0.8)));
      rows = Math.max(18, Math.floor(height / (CELL_SIZE * 1.08)));

      if (!fadeInQueued) {
        fadeInQueued = true;
        requestAnimationFrame(() => {
          canvas.style.opacity = "1";
        });
      }
    };

    const drawFrame = (timestamp: number) => {
      if (isDisposed) return;

      if (timestamp - lastFrame < 1000 / MAX_FPS) {
        frameId = window.requestAnimationFrame(drawFrame);
        return;
      }
      lastFrame = timestamp;

      context.clearRect(0, 0, width, height);
      const time = timestamp / 1000;
      const stepX = width / cols;
      const stepY = height / rows;
      const pulse = Math.max(0, pointer.pulse - 0.035);
      pointer.pulse = pulse;

      for (let row = 0; row < rows; row += 1) {
        for (let col = 0; col < cols; col += 1) {
          const px = (col + 0.5) * stepX;
          const py = (row + 0.5) * stepY;
          const nx = cols > 1 ? (col / (cols - 1)) * 2 - 1 : 0;
          const ny = rows > 1 ? (row / (rows - 1)) * 2 - 1 : 0;

          let intensity = sampleField(nx, ny, time);
          const vignette = clamp(1 - Math.sqrt(nx * nx + ny * ny) * 0.58, 0.18, 1);
          intensity *= vignette;

          if (pointer.active) {
            const dx = px / width - pointer.x;
            const dy = py / height - pointer.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            const ripple = Math.max(0, 1 - distance / 0.34);
            intensity += ripple * (0.22 + pulse * 0.28);
          }

          intensity = clamp(intensity, 0, 1);
          const charIndex = Math.min(CHARSET.length - 1, Math.floor(intensity * (CHARSET.length - 1)));
          const glyph = CHARSET[charIndex];
          const alpha = clamp(intensity * 1.3, 0.08, 0.92);
          const shade = Math.round(180 + intensity * 70);

          context.fillStyle = `rgba(${shade}, ${shade}, ${shade}, ${alpha})`;
          context.fillText(glyph, px, py);
        }
      }

      frameId = window.requestAnimationFrame(drawFrame);
    };

    const handlePointerMove = (event: PointerEvent) => {
      const rect = mount.getBoundingClientRect();
      pointer.active = true;
      pointer.x = clamp((event.clientX - rect.left) / Math.max(rect.width, 1), 0, 1);
      pointer.y = clamp((event.clientY - rect.top) / Math.max(rect.height, 1), 0, 1);
    };

    const handlePointerLeave = () => {
      pointer.active = false;
    };

    const handlePointerDown = () => {
      pointer.pulse = 1;
    };

    const resizeObserver = new ResizeObserver(setCanvasSize);
    resizeObserver.observe(mount);
    mount.addEventListener("pointermove", handlePointerMove);
    mount.addEventListener("pointerleave", handlePointerLeave);
    mount.addEventListener("pointerdown", handlePointerDown);

    setCanvasSize();
    frameId = window.requestAnimationFrame(drawFrame);

    return () => {
      isDisposed = true;
      resizeObserver.disconnect();
      mount.removeEventListener("pointermove", handlePointerMove);
      mount.removeEventListener("pointerleave", handlePointerLeave);
      mount.removeEventListener("pointerdown", handlePointerDown);
      window.cancelAnimationFrame(frameId);
    };
  }, []);

  return (
    <div
      ref={mountRef}
      className={`pointer-events-auto absolute inset-0 overflow-hidden ${className ?? ""}`.trim()}
    >
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        className="absolute inset-0 h-full w-full opacity-0 transition-opacity duration-700 [mask-image:linear-gradient(to_bottom,black_0%,black_84%,transparent_100%)] [-webkit-mask-image:linear-gradient(to_bottom,black_0%,black_84%,transparent_100%)]"
      />
    </div>
  );
}
