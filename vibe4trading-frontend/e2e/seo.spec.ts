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
    await expect(ogTitle.first()).toBeAttached();
    const content = await ogTitle.first().getAttribute("content");
    expect(content).toContain("Vibe4Trading");
  });

  test("homepage has JSON-LD structured data", async ({ page }) => {
    await gotoPath(page, "/");
    const jsonLd = page.locator('script[type="application/ld+json"]');
    await expect(jsonLd.first()).toBeAttached();
    const count = await jsonLd.count();
    expect(count).toBeGreaterThanOrEqual(1);
    const allContents: string[] = [];
    for (let i = 0; i < count; i++) {
      allContents.push((await jsonLd.nth(i).textContent()) ?? "");
    }
    const combined = allContents.join("");
    expect(combined).toContain("Organization");
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

  test("site.webmanifest is accessible and valid", async ({ page }) => {
    const { webOrigin } = origins();
    const res = await page.request.get(`${webOrigin}/site.webmanifest`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.name).toBe("Vibe4Trading");
    expect(body.theme_color).toBe("#020304");
    expect(body.icons).toHaveLength(3);
  });

  test("apple-touch-icon.png is accessible", async ({ page }) => {
    const { webOrigin } = origins();
    const res = await page.request.get(`${webOrigin}/apple-touch-icon.png`);
    expect(res.status()).toBe(200);
  });

  test("favicon PNGs are accessible", async ({ page }) => {
    const { webOrigin } = origins();
    const res16 = await page.request.get(`${webOrigin}/favicon-16x16.png`);
    expect(res16.status()).toBe(200);
    const res32 = await page.request.get(`${webOrigin}/favicon-32x32.png`);
    expect(res32.status()).toBe(200);
  });

  test("noscript content contains navigation links", async ({ page }) => {
    const { webOrigin } = origins();
    const res = await page.request.get(webOrigin);
    const html = await res.text();
    expect(html).toContain("<noscript>");
    expect(html).toContain("/arena");
    expect(html).toContain("/leaderboard");
    expect(html).toContain("/contact");
    expect(html).toContain("/privacy");
  });

  test("theme-color meta tag is present", async ({ page }) => {
    await gotoPath(page, "/");
    const themeColor = page.locator('meta[name="theme-color"]');
    await expect(themeColor).toBeAttached();
    const content = await themeColor.getAttribute("content");
    expect(content).toBe("#020304");
  });

  test("sitemap has lastmod and no changefreq or priority", async ({ page }) => {
    const { webOrigin } = origins();
    const res = await page.request.get(`${webOrigin}/sitemap.xml`);
    expect(res.status()).toBe(200);
    const body = await res.text();
    expect(body).toContain("<lastmod>");
    expect(body).not.toContain("<changefreq>");
    expect(body).not.toContain("<priority>");
  });

  test("arena page has WebApplication JSON-LD", async ({ page }) => {
    await gotoPath(page, "/arena");
    const jsonLd = page.locator('script[type="application/ld+json"]');
    await expect(jsonLd.first()).toBeAttached();
    const content = await jsonLd.first().textContent();
    expect(content).toContain("WebApplication");
  });

  test("leaderboard page has Dataset JSON-LD", async ({ page }) => {
    await gotoPath(page, "/leaderboard");
    const jsonLd = page.locator('script[type="application/ld+json"]');
    await expect(jsonLd.first()).toBeAttached();
    const content = await jsonLd.first().textContent();
    expect(content).toContain("Dataset");
  });

  test("contact page has ContactPage JSON-LD", async ({ page }) => {
    await gotoPath(page, "/contact");
    const jsonLd = page.locator('script[type="application/ld+json"]');
    await expect(jsonLd.first()).toBeAttached();
    const content = await jsonLd.first().textContent();
    expect(content).toContain("ContactPage");
  });

  test("404 page has noindex", async ({ page }) => {
    await gotoPath(page, "/nonexistent-route-xyz");
    const noindex = page.locator('meta[name="robots"][content*="noindex"]');
    await expect(noindex).toBeAttached();
  });

  test("twitter:site meta tag is present on homepage", async ({ page }) => {
    await gotoPath(page, "/");
    const twitterSite = page.locator('meta[name="twitter:site"]');
    await expect(twitterSite).toBeAttached();
    const content = await twitterSite.getAttribute("content");
    expect(content).toBe("@vibe4trading");
  });
});
