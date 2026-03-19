import { expect, test } from "@playwright/test";
import { gotoPath, origins } from "./ui-helpers";

test.describe("i18n locale switching", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(origins().webOrigin);
    await page.evaluate(() => localStorage.clear());
  });

  test("language switcher toggles between en and zh", async ({ page }) => {
    await gotoPath(page, "/");
    
    const switcher = page.getByRole("button", { name: "Switch language" });
    await expect(switcher).toBeVisible();
    await expect(switcher).toContainText("EN");
    
    await switcher.click();
    await expect(switcher).toContainText("中文");
    
    await switcher.click();
    await expect(switcher).toContainText("EN");
  });

  test("locale persists in localStorage", async ({ page }) => {
    await gotoPath(page, "/");
    
    const switcher = page.getByRole("button", { name: "Switch language" });
    await switcher.click();
    
    const storedLocale = await page.evaluate(() => localStorage.getItem("i18nextLng"));
    expect(storedLocale).toBe("zh");
    
    await page.reload();
    await expect(switcher).toContainText("中文");
  });

  test("navigation items display in correct locale", async ({ page }) => {
    await gotoPath(page, "/");
    
    await expect(page.getByRole("link", { name: /HOME/i })).toBeVisible();
    
    const switcher = page.getByRole("button", { name: "Switch language" });
    await switcher.click();
    await page.waitForTimeout(500);
    
    await expect(page.getByRole("link", { name: "首页" })).toBeVisible();
  });

  test("locale persists across page navigation", async ({ page }) => {
    await gotoPath(page, "/");
    
    const switcher = page.getByRole("button", { name: "Switch language" });
    await switcher.click();
    await expect(switcher).toContainText("中文");
    
    await gotoPath(page, "/arena");
    const arenaSwitcher = page.getByRole("button", { name: "Switch language" });
    await expect(arenaSwitcher).toContainText("中文");
    
    await gotoPath(page, "/leaderboard");
    const leaderboardSwitcher = page.getByRole("button", { name: "Switch language" });
    await expect(leaderboardSwitcher).toContainText("中文");
  });

  test("arena page content translates", async ({ page }) => {
    await gotoPath(page, "/arena");
    await page.waitForLoadState("networkidle");
    
    const switcher = page.getByRole("button", { name: "Switch language" });
    await switcher.click();
    await page.waitForTimeout(500);
    
    await expect(switcher).toContainText("中文");
  });

  test("leaderboard page translates", async ({ page }) => {
    await gotoPath(page, "/leaderboard");
    await page.waitForLoadState("networkidle");
    
    const switcher = page.getByRole("button", { name: "Switch language" });
    await expect(switcher).toBeVisible();
    
    await switcher.click();
    await expect(switcher).toContainText("中文");
  });

  test("runs page translates", async ({ page }) => {
    await gotoPath(page, "/runs");
    await page.waitForLoadState("networkidle");
    
    const switcher = page.getByRole("button", { name: "Switch language" });
    await switcher.click();
    await expect(switcher).toContainText("中文");
  });

  test("admin page translates", async ({ page }) => {
    await gotoPath(page, "/admin/models");
    await page.waitForLoadState("networkidle");
    
    const switcher = page.getByRole("button", { name: "Switch language" });
    await switcher.click();
    await expect(switcher).toContainText("中文");
  });

  test("backend API accepts locale headers", async ({ page }) => {
    await gotoPath(page, "/");
    
    const { backendOrigin } = origins();
    
    const responseEn = await page.request.get(`${backendOrigin}/api/invalid-endpoint`, {
      headers: { "Accept-Language": "en" },
    });
    expect(responseEn.status()).toBe(404);
    
    const responseZh = await page.request.get(`${backendOrigin}/api/invalid-endpoint`, {
      headers: { "Accept-Language": "zh" },
    });
    expect(responseZh.status()).toBe(404);
  });

  test("html lang attribute updates with locale", async ({ page }) => {
    await gotoPath(page, "/");
    
    let htmlLang = await page.evaluate(() => document.documentElement.lang);
    expect(htmlLang).toBe("en");
    
    const switcher = page.getByRole("button", { name: "Switch language" });
    await switcher.click();
    
    htmlLang = await page.evaluate(() => document.documentElement.lang);
    expect(htmlLang).toBe("zh");
  });

  test("locale switcher works on all major pages", async ({ page }) => {
    const pages = ["/", "/arena", "/leaderboard", "/runs"];
    
    for (const path of pages) {
      await gotoPath(page, path);
      await page.waitForLoadState("networkidle");
      
      const switcher = page.getByRole("button", { name: "Switch language" });
      await expect(switcher).toBeVisible();
      
      const currentText = await switcher.textContent();
      if (currentText === "EN") {
        await switcher.click();
        await expect(switcher).toContainText("中文");
      }
    }
  });
});
