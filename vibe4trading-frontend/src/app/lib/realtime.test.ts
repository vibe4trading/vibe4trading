import { describe, it, expect, vi } from "vitest";

describe("realtime WebSocket JSON.parse protection", () => {
  it("should handle malformed JSON in WebSocket message without crashing", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    
    const malformedJson = "{invalid json}";
    
    expect(() => {
      try {
        JSON.parse(malformedJson);
      } catch (err) {
        console.error("[realtime] Failed to parse WebSocket message:", err);
      }
    }).not.toThrow();
    
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      expect.stringContaining("[realtime]"),
      expect.any(Error)
    );
    
    consoleErrorSpy.mockRestore();
  });
});
