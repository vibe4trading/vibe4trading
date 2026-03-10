import { expect, test } from "@playwright/test";

import { gotoPath, origins } from "./ui-helpers";

test.describe("SEO", () => {
  test("robots.txt is accessible and contains sitemap reference", async ({ page }) => {
    const { webOrigin } = origins();
    const res = await page.request.get(`${webOrigin}/robots.txt`);
    expect(res.status()).toBe(200);
    const body = await res.text();
    expect(body).toContain("Sitemap:");
  });

  test("sitemap.xml is accessible and contains expected URLs", async ({ page }) => {
    const { webOrigin } = origins();
    const res = await page.request.get(`${webOrigin}/sitemap.xml`);
    expect(res.status()).toBe(200);
    const body = await res.text();
    const locCount = (body.match(/<loc>/g) || []).length;
    expect(locCount).toBe(5);
  });

  test("favicon.ico is accessible", async ({ page }) => {
    const { webOrigin } = origins();
    const res = await page.request.get(`${webOrigin}/favicon.ico`);
    expect(res.status()).toBe(200);
  });

  test("og-image.png is accessible", async ({ page }) => {
    const { webOrigin } = origins();
    const res = await page.request.get(`${webOrigin}/og-image.png`);
    expect(res.status()).toBe(200);
  });

  test("homepage has correct title", async ({ page }) => {
    await gotoPath(page, "/");
    const title = await page.title();
    expect(title).toContain("Vibe4Trading");
  });

  test("arena page has unique title", async ({ page }) => {
    await gotoPath(page, "/arena");
    const arenaTitle = await page.title();
    expect(arenaTitle).toContain("Arena");
  });

  test("homepage has OG tags", async ({ page }) => {
    await gotoPath(page, "/");
    const ogTitle = page.locator('meta[property="og:title"]');
    await expect(ogTitle).toBeAttached();
  });

  test("homepage has JSON-LD structured data", async ({ page }) => {
    await gotoPath(page, "/");
    const jsonLd = page.locator('script[type="application/ld+json"]');
    await expect(jsonLd).toBeAttached();
    const content = await jsonLd.textContent();
    expect(content).toBeTruthy();
    expect(content).toContain("Organization");
  });

  test("auth-gated route has noindex", async ({ page }) => {
    await gotoPath(page, "/runs");
    const noindex = page.locator('meta[name="robots"][content*="noindex"]');
    await expect(noindex).toBeAttached();
  });

  test("per-page canonical URLs differ", async ({ page }) => {
    await gotoPath(page, "/");
    const homeCanonical = await page.locator('link[rel="canonical"]').getAttribute("href");
    expect(homeCanonical).toBeTruthy();

    await gotoPath(page, "/arena");
    const arenaCanonical = await page.locator('link[rel="canonical"]').getAttribute("href");
    expect(arenaCanonical).toBeTruthy();

    expect(homeCanonical).not.toBe(arenaCanonical);
  });
});
