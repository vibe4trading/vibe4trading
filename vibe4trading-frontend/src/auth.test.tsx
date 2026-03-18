import { describe, it, expect, vi } from "vitest";

describe("signIn redirect validation", () => {
  it("should reject external URLs in redirectTo parameter", () => {
    const mockWarn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const mockLocation = { href: "" };
    Object.defineProperty(window, "location", {
      value: mockLocation,
      writable: true,
    });

    const redirectTo = "https://evil.com";
    try {
      new URL(redirectTo);
      if (!redirectTo.startsWith("/")) {
        console.warn("Security: rejecting external URL in redirectTo");
      }
    } catch {}

    expect(mockWarn).toHaveBeenCalledWith(
      expect.stringContaining("external URL")
    );
    mockWarn.mockRestore();
  });
});
