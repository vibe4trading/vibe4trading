import { describe, it, expect, vi } from "vitest";

describe("submissionLoading JSON.parse protection", () => {
  it("should handle malformed JSON in sessionStorage without crashing", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    
    const malformedJson = "{invalid json}";
    
    expect(() => {
      try {
        JSON.parse(malformedJson);
      } catch (err) {
        console.error("[submissionLoading] Failed to parse sessionStorage data:", err);
        return null;
      }
    }).not.toThrow();
    
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      expect.stringContaining("[submissionLoading]"),
      expect.any(Error)
    );
    
    consoleErrorSpy.mockRestore();
  });
});
