import { describe, it, expect } from "vitest";
import { isoFromLocalInput } from "../src/app/lib/v4t";

describe("v4t utilities", () => {
  describe("isoFromLocalInput", () => {
    it("converts local datetime string to ISO", () => {
      const result = isoFromLocalInput("2024-01-01T12:00");
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
    });

    it("returns valid ISO 8601 format", () => {
      const result = isoFromLocalInput("2024-06-15T14:30");
      const parsed = new Date(result);
      expect(parsed.toISOString()).toBe(result);
    });
  });
});
