import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { usePrerenderReady } from "../src/app/hooks/usePrerenderReady";

describe("usePrerenderReady", () => {
  let originalPrerenderReady: boolean | undefined;

  beforeEach(() => {
    originalPrerenderReady = window.prerenderReady;
    window.prerenderReady = false;
  });

  afterEach(() => {
    window.prerenderReady = originalPrerenderReady;
  });

  it("does not signal readiness when isReady is false", () => {
    renderHook(() => usePrerenderReady(false));
    expect(window.prerenderReady).toBe(false);
  });

  it("signals readiness immediately when isReady is true (static page pattern)", () => {
    renderHook(() => usePrerenderReady(true));
    expect(window.prerenderReady).toBe(true);
  });

  it("transitions from false to true when isReady changes (data page pattern)", () => {
    const { rerender } = renderHook(
      ({ ready }) => usePrerenderReady(ready),
      { initialProps: { ready: false } },
    );

    expect(window.prerenderReady).toBe(false);

    rerender({ ready: true });
    expect(window.prerenderReady).toBe(true);
  });

  it("does not revert to false once signalled", () => {
    const { rerender } = renderHook(
      ({ ready }) => usePrerenderReady(ready),
      { initialProps: { ready: true } },
    );

    expect(window.prerenderReady).toBe(true);

    rerender({ ready: false });
    expect(window.prerenderReady).toBe(true);
  });

  it("only writes to window.prerenderReady once across multiple true renders", () => {
    const { rerender } = renderHook(
      ({ ready }) => usePrerenderReady(ready),
      { initialProps: { ready: false } },
    );

    rerender({ ready: true });
    expect(window.prerenderReady).toBe(true);

    // Externally reset the global to verify the hook's ref guard prevents re-setting
    window.prerenderReady = false;

    rerender({ ready: true });
    expect(window.prerenderReady).toBe(false);
  });
});
