import { describe, expect, it } from "vitest";

import { getSubmissionStatusDisplay } from "../src/app/lib/submissionStatus";

describe("submission status display", () => {
  it("treats a pending submission with no start time as queued", () => {
    expect(getSubmissionStatusDisplay({ status: "pending", startedAt: null })).toMatchObject({
      label: "Queued",
      headline: "Queued for execution",
      isQueued: true,
    });
  });

  it("treats a running submission as active work", () => {
    expect(
      getSubmissionStatusDisplay({
        status: "running",
        startedAt: "2026-03-06T20:15:00Z",
      }),
    ).toMatchObject({
      label: "Running",
      headline: "Trial in progress",
      isQueued: false,
    });
  });
});
