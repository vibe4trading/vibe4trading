import { expect, test } from "@playwright/test";

import { gotoPath, origins, summonDemoArenaSubmission } from "./ui-helpers";

test.describe.configure({ mode: "serial" });

test("tournament e2e: arena submission runs with fake LLM behaviors", async ({ page }) => {
  const submissionId = await test.step("arena: summon demo submission", async () => {
    return await summonDemoArenaSubmission(page);
  });

  await test.step("leaderboard: submission appears on tournament page", async () => {
    await gotoPath(page, "/arena");
    await expect(page.getByText(submissionId.slice(0, 8))).toBeVisible({ timeout: 120_000 });
  });

  await test.step("backend: submission expands into runs", async () => {
    const { backendOrigin } = origins();

    const res = await page.request.get(`${backendOrigin}/arena/submissions/${submissionId}`, {
      headers: { accept: "application/json" },
    });
    expect(res.ok()).toBeTruthy();
    const body = (await res.json()) as {
      status: string;
      runs: Array<{ run_id: string; status: string }>;
    };

    expect(body.status).toBe("finished");
    expect(body.runs.length).toBeGreaterThan(0);
    for (const r of body.runs) expect(r.status).toBe("finished");
  });

  await test.step("backend: decisions stream exists", async () => {
    const { backendOrigin } = origins();
    const detailRes = await page.request.get(`${backendOrigin}/arena/submissions/${submissionId}`, {
      headers: { accept: "application/json" },
    });
    expect(detailRes.ok()).toBeTruthy();
    const detail = (await detailRes.json()) as { runs: Array<{ run_id: string }> };

    const runIds = (detail.runs ?? []).map((r) => r.run_id).filter(Boolean);
    expect(runIds.length).toBeGreaterThan(0);

    let anyDecisions = false;
    for (const runId of runIds) {
      const decisionsRes = await page.request.get(`${backendOrigin}/runs/${runId}/decisions?limit=200`, {
        headers: { accept: "application/json" },
      });
      expect(decisionsRes.ok()).toBeTruthy();
      const decisions = (await decisionsRes.json()) as Array<{ accepted?: boolean; reject_reason?: string | null }>;

      if (decisions.length > 0) {
        anyDecisions = true;
        break;
      }
    }

    expect(anyDecisions).toBeTruthy();
  });

  await test.step("fake-llm: stats show retries + malformed outputs happened", async () => {
    const { llmOrigin } = origins();
    expect(llmOrigin).toBeTruthy();

    const statsRes = await page.request.get(`${llmOrigin}/stats`, {
      headers: { accept: "application/json" },
    });
    expect(statsRes.ok()).toBeTruthy();
    const stats = (await statsRes.json()) as {
      requests: number;
      simulated429: number;
      simulatedMalformedJson: number;
    };

    expect(stats.requests).toBeGreaterThan(0);
    expect(stats.simulated429).toBeGreaterThan(0);
    expect(stats.simulatedMalformedJson).toBeGreaterThan(0);
  });
});
