import { describe, it, expect } from "vitest";
import { buildNoobPrompt } from "./PromptInput";

describe("PromptInput", () => {
  it("test_validates_selections_object", () => {
    const malformed = { tradingStyle: undefined, timeHorizon: undefined, riskTolerance: undefined } as any;
    const result = buildNoobPrompt(malformed);
    
    expect(result).not.toContain("undefined");
    expect(result).toContain("balanced");
    expect(result).toContain("medium-term");
    expect(result).toContain("moderate");
  });
});
