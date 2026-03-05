import { expect, test } from "@playwright/test";

import {
  createArenaSubmission,
  gotoPath,
  origins,
  startAndStopLive,
  waitForRunFinishedOnDetail,
} from "./ui-helpers";

test.describe.configure({ mode: "serial" });

test("end-to-end smoke", async ({ page }) => {
  const submissionId = await test.step("tournament: create + inspect first scenario run", async () => {
    const created = await createArenaSubmission(page);

    const { backendOrigin } = origins();
    const detailRes = await page.request.get(`${backendOrigin}/arena/submissions/${created}`, {
      headers: { accept: "application/json" },
    });
    expect(detailRes.ok()).toBeTruthy();
    const detail = (await detailRes.json()) as { runs: Array<{ run_id: string }> };
    const runId = detail.runs[0]?.run_id;
    expect(runId).toBeTruthy();

    await waitForRunFinishedOnDetail(page, String(runId));
    await expect(page.getByText(/Summary/i)).toBeVisible();
    await expect(page.locator("table").first()).toBeVisible();
    return created;
  });

  await test.step("live: start + stop", async () => {
    await startAndStopLive(page);
  });

  await test.step("leaderboard: tournament run appears on tournament page", async () => {
    await gotoPath(page, "/arena");
    await expect(page.getByText(submissionId.slice(0, 8))).toBeVisible({ timeout: 120_000 });
  });
});
