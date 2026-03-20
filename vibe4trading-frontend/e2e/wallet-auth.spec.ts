import { expect, test } from "@playwright/test";
import { gotoPath, origins } from "./ui-helpers";

test.describe("Wallet Authentication", () => {
  test.beforeEach(async ({ page }) => {
    // Mock JoyID SDK
    await page.addInitScript(() => {
      (window as any).joyid = {
        connect: async () => "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        signMessage: async (msg: string) => ({
          signature: "0x" + "a".repeat(130),
          message: msg,
        }),
      };
    });
  });

  test("wallet login flow", async ({ page }) => {
    const { webOrigin } = origins();
    
    // Mock challenge endpoint
    await page.route(`${webOrigin}/api/v4t/auth/wallet/challenge`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          nonce: "a".repeat(64),
          message: "Sign in to Vibe4Trading\n\nNonce: " + "a".repeat(64) + "\nChain ID: 1",
        }),
      });
    });

    // Mock verify endpoint
    await page.route(`${webOrigin}/api/v4t/auth/wallet/verify`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true }),
      });
    });

    await gotoPath(page, "/");
    
    const walletButton = page.getByRole("button", { name: /wallet/i });
    await walletButton.click();

    await expect(page).toHaveURL("/", { timeout: 10_000 });
  });

  test("wallet linking from profile", async ({ page }) => {
    const { webOrigin } = origins();
    
    await page.route(`${webOrigin}/api/v4t/auth/wallet/challenge`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          nonce: "b".repeat(64),
          message: "Sign in to Vibe4Trading\n\nNonce: " + "b".repeat(64) + "\nChain ID: 1",
        }),
      });
    });

    await page.route(`${webOrigin}/api/v4t/me/link-wallet`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ wallet_address: "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0" }),
      });
    });

    await gotoPath(page, "/profile");
    
    const linkButton = page.getByRole("button", { name: /link wallet/i });
    await linkButton.click();

    await expect(page.getByText(/0x742d35/i)).toBeVisible({ timeout: 10_000 });
  });

  test("wallet unlinking", async ({ page }) => {
    const { webOrigin } = origins();
    
    await page.route(`${webOrigin}/api/v4t/me/unlink-wallet`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true }),
      });
    });

    await gotoPath(page, "/profile");
    
    const unlinkButton = page.getByRole("button", { name: /unlink/i });
    if (await unlinkButton.isVisible()) {
      await unlinkButton.click();
      await expect(page.getByRole("button", { name: /link wallet/i })).toBeVisible({ timeout: 10_000 });
    }
  });
});
