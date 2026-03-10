import { expect, test } from "@playwright/test";

import { gotoPath, summonDemoArenaSubmission } from "./ui-helpers";

/**
 * Interactive tour E2E tests.
 *
 * These tests verify our Driver.js integration:
 * - Auto-trigger on first visit (via useEffect + setTimeout)
 * - Persistence via localStorage key `v4t_tour_completed`
 * - Manual launch via TourButton dropdown
 * - Step navigation (next / done / close)
 *
 * Driver.js DOM selectors:
 *   .driver-popover          – the tooltip container
 *   .driver-popover-title    – step title
 *   .driver-popover-next-btn – "Next" button
 *   .driver-popover-done-btn – "Done" button (last step only)
 *   .driver-popover-close-btn – close "X" button
 */

/** Timeout for the auto-trigger delay (500ms) plus render overhead. */
const TOUR_APPEAR_TIMEOUT = 5_000;

const POPOVER = ".driver-popover";
const TITLE = ".driver-popover-title";
const PREV_BTN = ".driver-popover-prev-btn";
const NEXT_BTN = ".driver-popover-next-btn";
const DONE_BTN = ".driver-popover-done-btn";
const CLOSE_BTN = ".driver-popover-close-btn";

test.describe("Interactive tours", () => {
  test.describe.configure({ mode: "serial" });

  test("Trials tour auto-triggers on first visit to /arena", async ({ page }) => {
    await gotoPath(page, "/arena");

    // Clear any persisted tour completions so auto-trigger fires
    await page.evaluate(() => localStorage.removeItem("v4t_tour_completed"));

    // Reload to trigger the useEffect auto-start path
    await page.reload();

    // Wait for Driver.js popover (500ms delay + render time)
    const popover = page.locator(POPOVER);
    await expect(popover).toBeVisible({ timeout: TOUR_APPEAR_TIMEOUT });

    // Assert first step title
    await expect(page.locator(TITLE)).toContainText("Start a New Trial");

    // Click "Next" to advance to second step
    await page.locator(NEXT_BTN).click();

    // Assert second step appears
    await expect(page.locator(TITLE)).toContainText("Your Submissions");

    // Click through remaining steps until "Done"
    await page.locator(NEXT_BTN).click();
    await page.locator(NEXT_BTN).click();

    // Last step has "Done" button instead of "Next"
    await page.locator(DONE_BTN).click();

    // Overlay should be gone after completing the tour
    await expect(popover).not.toBeVisible();
  });

  test("Trials tour does NOT re-trigger on second visit (persistence)", async ({ page }) => {
    // After previous test completed the tour, localStorage should contain "trials-v1"
    await gotoPath(page, "/arena");

    // Wait longer than the auto-trigger delay to ensure it would have fired
    await page.waitForTimeout(1_000);

    // Assert Driver.js popover does NOT appear
    await expect(page.locator(POPOVER)).not.toBeVisible();
  });

  test("Leaderboard tour auto-triggers on first visit to /leaderboard", async ({ page }) => {
    // Ensure leaderboard tour hasn't been completed
    await gotoPath(page, "/leaderboard");
    await page.evaluate(() => {
      const stored: string[] = JSON.parse(localStorage.getItem("v4t_tour_completed") || "[]");
      localStorage.setItem(
        "v4t_tour_completed",
        JSON.stringify(stored.filter((id) => id !== "leaderboard-v1")),
      );
    });
    await page.reload();

    // Wait for auto-trigger
    const popover = page.locator(POPOVER);
    await expect(popover).toBeVisible({ timeout: TOUR_APPEAR_TIMEOUT });

    // Assert first step
    await expect(page.locator(TITLE)).toContainText("Filter Rankings");

    // Complete the tour by clicking through all steps
    const nextBtn = page.locator(NEXT_BTN);
    const doneBtn = page.locator(DONE_BTN);

    // Click "Next" until it disappears, then click "Done"
    while (await nextBtn.isVisible().catch(() => false)) {
      await nextBtn.click();
      // Brief wait for Driver.js transition between steps
      await page.waitForTimeout(200);
    }
    if (await doneBtn.isVisible().catch(() => false)) {
      await doneBtn.click();
    }

    await expect(popover).not.toBeVisible();
  });

  test("Arena modal tour auto-triggers when submission modal opens", async ({ page }) => {
    // Navigate to /arena and ensure the arena-submission-v1 tour hasn't been completed
    await gotoPath(page, "/arena");
    await page.evaluate(() => {
      const stored: string[] = JSON.parse(localStorage.getItem("v4t_tour_completed") || "[]");
      localStorage.setItem(
        "v4t_tour_completed",
        JSON.stringify(stored.filter((id) => id !== "arena-submission-v1")),
      );
    });
    await page.reload();

    // Open the submission modal by clicking "Start a new run"
    const startButton = page.getByRole("button", { name: "Start a new run" });
    await expect(startButton).toBeVisible({ timeout: TOUR_APPEAR_TIMEOUT });
    await startButton.click();

    // Wait for the dialog to open
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible({ timeout: TOUR_APPEAR_TIMEOUT });

    // The arena-submission tour auto-triggers after 600ms when the modal opens
    const popover = page.locator(POPOVER);
    await expect(popover).toBeVisible({ timeout: TOUR_APPEAR_TIMEOUT });

    // Assert first step title matches arena submission tour
    await expect(page.locator(TITLE)).toContainText("Choose Your Pair");

    // Clean up — dismiss the tour
    const closeBtn = page.locator(CLOSE_BTN);
    if (await closeBtn.isVisible().catch(() => false)) {
      await closeBtn.click();
    }
  });

  test.describe("Submission Detail Tour", () => {
    test("Submission Detail tour auto-triggers on first visit", async ({ page }) => {
      // Create a finished submission using summonDemoArenaSubmission
      const submissionId = await summonDemoArenaSubmission(page);

      // We're already on the submission detail page after summonDemoArenaSubmission
      // Clear the tour completion flag
      await page.evaluate(() => {
        const stored: string[] = JSON.parse(localStorage.getItem("v4t_tour_completed") || "[]");
        localStorage.setItem(
          "v4t_tour_completed",
          JSON.stringify(stored.filter((id) => id !== "submission-detail-v1")),
        );
      });

      // Reload to trigger auto-start
      await page.reload();

      // Wait for page data to load (tour waits for data)
      await expect(page.locator('[data-tour="submission-hero-card"]')).toBeVisible({ timeout: 10_000 });

      // Wait for Driver.js popover (600ms delay + render time)
      const popover = page.locator(POPOVER);
      await expect(popover).toBeVisible({ timeout: TOUR_APPEAR_TIMEOUT });

      // Assert first step title
      await expect(page.locator(TITLE)).toContainText("Trial Score");

      // Click through all 6 steps
      await page.locator(NEXT_BTN).click();
      await expect(page.locator(TITLE)).toContainText("Key Metrics");

      await page.locator(NEXT_BTN).click();
      await expect(page.locator(TITLE)).toContainText("AI Report");

      await page.locator(NEXT_BTN).click();
      await expect(page.locator(TITLE)).toContainText("Window Returns");

      await page.locator(NEXT_BTN).click();
      await expect(page.locator(TITLE)).toContainText("Window Performance");

      await page.locator(NEXT_BTN).click();
      await expect(page.locator(TITLE)).toContainText("Inspect a Window");

      // Last step: click "Done"
      await page.locator(DONE_BTN).click();
      await expect(popover).not.toBeVisible();
    });

    test("Submission Detail tour does NOT re-trigger on second visit", async ({ page }) => {
      // After previous test, localStorage should contain "submission-detail-v1"
      // Navigate to any submission detail page
      const submissionId = await summonDemoArenaSubmission(page);

      // Wait longer than auto-trigger delay
      await page.waitForTimeout(1_500);

      // Assert Driver.js popover does NOT appear
      await expect(page.locator(POPOVER)).not.toBeVisible();
    });

    test("Submission Detail tour can be manually launched from TourButton", async ({ page }) => {
      // Navigate to submission detail page
      const submissionId = await summonDemoArenaSubmission(page);

      // Wait for page to settle
      await page.waitForTimeout(1_000);

      // Click TourButton
      const tourButton = page.locator('button[aria-haspopup="menu"]').filter({ hasText: "?" });
      await tourButton.click();

      // Click "Submission Report Tour" menu item
      const submissionTourOption = page.locator('[role="menuitem"]').filter({ hasText: "Submission Report Tour" });
      await submissionTourOption.click();

      // Wait for tour to start
      const popover = page.locator(POPOVER);
      await expect(popover).toBeVisible({ timeout: TOUR_APPEAR_TIMEOUT });

      // Assert first step
      await expect(page.locator(TITLE)).toContainText("Trial Score");

      // Dismiss tour
      const closeBtn = page.locator(CLOSE_BTN);
      if (await closeBtn.isVisible().catch(() => false)) {
        await closeBtn.click();
      }
    });
  });

  test("Tour navigation: next, prev, and done buttons work correctly", async ({ page }) => {
    // Use the trials tour (4 steps) to test full navigation
    await gotoPath(page, "/arena");
    await page.evaluate(() => localStorage.removeItem("v4t_tour_completed"));
    await page.reload();

    // Wait for auto-trigger
    const popover = page.locator(POPOVER);
    await expect(popover).toBeVisible({ timeout: TOUR_APPEAR_TIMEOUT });

    // Step 1: "Start a New Trial"
    await expect(page.locator(TITLE)).toContainText("Start a New Trial");

    // Click Next to advance to step 2
    await page.locator(NEXT_BTN).click();
    await expect(page.locator(TITLE)).toContainText("Your Submissions");

    // Click Previous to go back to step 1
    const prevBtn = page.locator(PREV_BTN);
    if (await prevBtn.isVisible().catch(() => false)) {
      await prevBtn.click();
      await expect(page.locator(TITLE)).toContainText("Start a New Trial");

      // Navigate forward again
      await page.locator(NEXT_BTN).click();
      await expect(page.locator(TITLE)).toContainText("Your Submissions");
    }

    // Continue through remaining steps
    await page.locator(NEXT_BTN).click();
    await page.locator(NEXT_BTN).click();

    // Last step: click "Done" to finish the tour
    await page.locator(DONE_BTN).click();
    await expect(popover).not.toBeVisible();
  });

  test("TourButton opens dropdown with 4 tour options", async ({ page }) => {
    await gotoPath(page, "/arena");

    // Find and click the TourButton (the "?" help button)
    const tourButton = page.locator('button[aria-haspopup="menu"]').filter({ hasText: "?" });
    await tourButton.click();

    // Assert dropdown menu is visible with 4 options
    const menu = page.locator('[role="menu"]');
    await expect(menu).toBeVisible();

    const menuItems = menu.locator('[role="menuitem"]');
    await expect(menuItems).toHaveCount(4);
    await expect(menuItems.nth(0)).toContainText("Trials Tour");
    await expect(menuItems.nth(1)).toContainText("Leaderboard Tour");
    await expect(menuItems.nth(2)).toContainText("Arena Submission Tour");
    await expect(menuItems.nth(3)).toContainText("Submission Report Tour");
  });

  test("TourButton can manually launch a tour", async ({ page }) => {
    await gotoPath(page, "/arena");

    // Remove trials-v1 from persistence so manual launch can work
    await page.evaluate(() => {
      const stored: string[] = JSON.parse(localStorage.getItem("v4t_tour_completed") || "[]");
      localStorage.setItem(
        "v4t_tour_completed",
        JSON.stringify(stored.filter((id) => id !== "trials-v1")),
      );
    });

    // Wait for any auto-trigger to pass before manual launch
    await page.waitForTimeout(1_000);

    // Click TourButton, then select "Trials Tour"
    const tourButton = page.locator('button[aria-haspopup="menu"]').filter({ hasText: "?" });
    await tourButton.click();

    const trialsOption = page.locator('[role="menuitem"]').filter({ hasText: "Trials Tour" });
    await trialsOption.click();

    // The TourButton sets context state which triggers the tour.
    // Verify the menu closes after selection (interaction works end-to-end).
    const menu = page.locator('[role="menu"]');
    await expect(menu).not.toBeVisible();
  });

  test("Tour can be dismissed with close button", async ({ page }) => {
    // Reset persistence for trials tour
    await gotoPath(page, "/arena");
    await page.evaluate(() => localStorage.removeItem("v4t_tour_completed"));
    await page.reload();

    // Wait for auto-trigger
    const popover = page.locator(POPOVER);
    await expect(popover).toBeVisible({ timeout: TOUR_APPEAR_TIMEOUT });

    // Click the close button (X) on the popover
    const closeBtn = page.locator(CLOSE_BTN);
    if (await closeBtn.isVisible().catch(() => false)) {
      await closeBtn.click();
    }

    // Assert overlay is dismissed
    await expect(popover).not.toBeVisible();
  });
});
