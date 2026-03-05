import { expect, test } from "@playwright/test";

import { gotoPath, origins } from "./ui-helpers";

test.describe("Error Scenarios", () => {
  test("datasets page is removed (404)", async ({ page }) => {
    const { webOrigin } = origins();
    const res = await page.goto(`${webOrigin}/datasets`);
    expect(res?.status()).toBe(404);
  });

  test("tournament run creation validates prompt", async ({ page }) => {
    await gotoPath(page, "/arena");

    const startButton = page.getByRole("button", { name: "Start a new run" });
    await expect(startButton).toBeEnabled({ timeout: 60_000 });
    await startButton.click();

    const dialog = page.getByRole("dialog", { name: "Start new run" });
    await expect(dialog).toBeVisible({ timeout: 10_000 });

    await dialog.getByRole("button", { name: /^Start run$/ }).click();

    await expect(
      dialog.getByText(/prompt is required/i),
    ).toBeVisible({ timeout: 5000 });
  });

  test("navigation to non-existent run shows error", async ({ page }) => {
    await gotoPath(page, "/runs/00000000-0000-0000-0000-000000000000");

    await expect(
      page.getByText(/not found|error|failed/i)
    ).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Edge Cases", () => {
  test("nav does not show datasets", async ({ page }) => {
    await gotoPath(page, "/");
    await expect(page.getByRole("link", { name: /^Datasets$/ })).toHaveCount(0);
  });

  test("nav does not show runs", async ({ page }) => {
    await gotoPath(page, "/");
    await expect(page.getByRole("link", { name: /^Runs$/ })).toHaveCount(0);
  });

  test("live dashboard handles no active run", async ({ page }) => {
    await gotoPath(page, "/live");

    await expect(page.getByRole("button", { name: /start live run/i })).toBeVisible({
      timeout: 5000,
    });
  });
});
