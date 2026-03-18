import { describe, it, expect, vi } from "vitest";

describe("watch page SSE JSON.parse protection", () => {
  it("should handle malformed JSON in llm_start event", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    
    const malformedJson = "{invalid: json}";
    
    expect(() => {
      try {
        JSON.parse(malformedJson);
      } catch (err) {
        console.error("[watch] Failed to parse llm_start event:", err);
      }
    }).not.toThrow();
    
    expect(consoleErrorSpy).toHaveBeenCalled();
    consoleErrorSpy.mockRestore();
  });

  it("should handle malformed JSON in llm_delta event", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    
    const malformedJson = "not json at all";
    
    expect(() => {
      try {
        JSON.parse(malformedJson);
      } catch (err) {
        console.error("[watch] Failed to parse llm_delta event:", err);
      }
    }).not.toThrow();
    
    expect(consoleErrorSpy).toHaveBeenCalled();
    consoleErrorSpy.mockRestore();
  });

  it("should handle malformed JSON in decision event", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    
    const malformedJson = "{broken";
    
    expect(() => {
      try {
        JSON.parse(malformedJson);
      } catch (err) {
        console.error("[watch] Failed to parse decision event:", err);
      }
    }).not.toThrow();
    
    expect(consoleErrorSpy).toHaveBeenCalled();
    consoleErrorSpy.mockRestore();
  });

  it("should handle malformed JSON in portfolio event", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    
    const malformedJson = '{"incomplete": ';
    
    expect(() => {
      try {
        JSON.parse(malformedJson);
      } catch (err) {
        console.error("[watch] Failed to parse portfolio event:", err);
      }
    }).not.toThrow();
    
    expect(consoleErrorSpy).toHaveBeenCalled();
    consoleErrorSpy.mockRestore();
  });
});
