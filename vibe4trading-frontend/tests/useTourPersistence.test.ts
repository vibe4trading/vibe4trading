import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTourPersistence } from "../src/app/hooks/useTourPersistence";

const STORAGE_KEY = "v4t_tour_completed";

function createMockLocalStorage() {
  const store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { Object.keys(store).forEach(k => delete store[k]); }),
    get length() { return Object.keys(store).length; },
    key: vi.fn((i: number) => Object.keys(store)[i] ?? null),
  };
}

describe("useTourPersistence", () => {
  let mockStorage: ReturnType<typeof createMockLocalStorage>;

  beforeEach(() => {
    mockStorage = createMockLocalStorage();
    Object.defineProperty(globalThis, "localStorage", {
      value: mockStorage,
      writable: true,
      configurable: true,
    });
  });

  it("hasCompleted returns false initially", () => {
    const { result } = renderHook(() => useTourPersistence("test-tour"));
    expect(result.current.hasCompleted()).toBe(false);
  });

  it("markCompleted marks tour and hasCompleted returns true", () => {
    const { result } = renderHook(() => useTourPersistence("test-tour"));
    
    act(() => {
      result.current.markCompleted();
    });
    
    expect(result.current.hasCompleted()).toBe(true);
  });

  it("reset removes tour", () => {
    const { result } = renderHook(() => useTourPersistence("test-tour"));
    
    act(() => {
      result.current.markCompleted();
    });
    expect(result.current.hasCompleted()).toBe(true);
    
    act(() => {
      result.current.reset();
    });
    expect(result.current.hasCompleted()).toBe(false);
  });

  it("tracks multiple tours independently", () => {
    const { result: tour1 } = renderHook(() => useTourPersistence("tour-1"));
    const { result: tour2 } = renderHook(() => useTourPersistence("tour-2"));
    
    act(() => {
      tour1.current.markCompleted();
    });
    
    expect(tour1.current.hasCompleted()).toBe(true);
    expect(tour2.current.hasCompleted()).toBe(false);
  });

  it("uses key v4t_tour_completed", () => {
    const { result } = renderHook(() => useTourPersistence("test-tour"));
    
    act(() => {
      result.current.markCompleted();
    });
    
    const stored = mockStorage.getItem(STORAGE_KEY);
    expect(stored).toBeTruthy();
    expect(JSON.parse(stored!)).toEqual(["test-tour"]);
  });

  it("stores as JSON array", () => {
    const { result: tour1 } = renderHook(() => useTourPersistence("tour-1"));
    const { result: tour2 } = renderHook(() => useTourPersistence("tour-2"));
    
    act(() => {
      tour1.current.markCompleted();
      tour2.current.markCompleted();
    });
    
    const stored = mockStorage.getItem(STORAGE_KEY);
    const parsed = JSON.parse(stored!);
    expect(Array.isArray(parsed)).toBe(true);
    expect(parsed).toContain("tour-1");
    expect(parsed).toContain("tour-2");
  });

  it("handles localStorage errors gracefully", () => {
    mockStorage.getItem.mockImplementation(() => {
      throw new Error("localStorage error");
    });
    
    const { result } = renderHook(() => useTourPersistence("test-tour"));
    expect(result.current.hasCompleted()).toBe(false);
  });
});
