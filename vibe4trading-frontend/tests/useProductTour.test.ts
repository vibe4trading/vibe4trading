import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";

vi.mock("driver.js", () => ({
  driver: vi.fn(() => ({ drive: vi.fn(), destroy: vi.fn() })),
}));
vi.mock("driver.js/dist/driver.css", () => ({}));
vi.mock("@/app/tours/tour.css", () => ({}));

import { useProductTour } from "../src/app/hooks/useProductTour";

describe("useProductTour", () => {
  it("returns start, stop, destroy", () => {
    const { result } = renderHook(() =>
      useProductTour([{ element: "#step1", popover: { title: "Step 1" } }])
    );

    expect(result.current).toHaveProperty("start");
    expect(result.current).toHaveProperty("stop");
    expect(result.current).toHaveProperty("destroy");
    expect(typeof result.current.start).toBe("function");
    expect(typeof result.current.stop).toBe("function");
    expect(typeof result.current.destroy).toBe("function");
  });

  it("renders without errors", () => {
    expect(() => {
      renderHook(() =>
        useProductTour([{ element: "#step1", popover: { title: "Step 1" } }])
      );
    }).not.toThrow();
  });

  it("cleans up on unmount", async () => {
    const { driver } = await import("driver.js");
    const mockDestroy = vi.fn();
    vi.mocked(driver).mockReturnValue({
      drive: vi.fn(),
      destroy: mockDestroy,
    } as any);

    const { result, unmount } = renderHook(() =>
      useProductTour([{ element: "#step1", popover: { title: "Step 1" } }])
    );

    act(() => {
      result.current.start();
    });

    unmount();
    expect(mockDestroy).toHaveBeenCalled();
  });
});
