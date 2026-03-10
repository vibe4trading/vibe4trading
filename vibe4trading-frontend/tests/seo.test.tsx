import { describe, it, expect, afterEach, vi, beforeAll } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";
import { HelmetProvider } from "react-helmet-async";
import { MemoryRouter } from "react-router-dom";
import { SEO } from "../src/app/components/SEO";

beforeAll(() => {
  const mockIntersectionObserver = vi.fn().mockImplementation((callback: IntersectionObserverCallback) => ({
    observe: vi.fn().mockImplementation((target: Element) => {
      callback(
        [{ isIntersecting: true, target } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );
    }),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));
  vi.stubGlobal("IntersectionObserver", mockIntersectionObserver);
});

beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
    fillRect: vi.fn(),
    clearRect: vi.fn(),
    putImageData: vi.fn(),
    getImageData: vi.fn().mockReturnValue({ data: new Uint8ClampedArray(0) }),
    createImageData: vi.fn().mockReturnValue({ data: new Uint8ClampedArray(0) }),
    drawImage: vi.fn(),
    scale: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    canvas: { width: 100, height: 100 },
  }) as any;
});

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <HelmetProvider>
      <MemoryRouter>{ui}</MemoryRouter>
    </HelmetProvider>,
  );
}

function getMeta(attr: string, value: string): HTMLMetaElement | null {
  return document.head.querySelector(`meta[${attr}="${value}"]`);
}

describe("SEO", () => {
  afterEach(() => {
    cleanup();
    document.head.innerHTML = "";
  });

  it("renders title with brand suffix", async () => {
    renderWithProviders(<SEO title="Arena" description="desc" />);

    await waitFor(() => {
      expect(document.title).toBe("Arena | Vibe4Trading");
    });
  });

  it("renders OG tags", async () => {
    renderWithProviders(
      <SEO title="Arena" description="Test description" canonicalPath="/arena" />,
    );

    await waitFor(() => {
      expect(getMeta("property", "og:title")?.getAttribute("content")).toBe(
        "Arena | Vibe4Trading",
      );
    });

    expect(getMeta("property", "og:description")?.getAttribute("content")).toBe(
      "Test description",
    );
    expect(getMeta("property", "og:image")?.getAttribute("content")).toBe(
      "https://vibe4trading.ai/og-image.png",
    );
  });

  it("renders Twitter Card tags", async () => {
    renderWithProviders(<SEO title="Arena" description="desc" />);

    await waitFor(() => {
      expect(getMeta("name", "twitter:card")?.getAttribute("content")).toBe(
        "summary_large_image",
      );
    });

    expect(getMeta("name", "twitter:title")?.getAttribute("content")).toBe(
      "Arena | Vibe4Trading",
    );
  });

  it("renders canonical link", async () => {
    renderWithProviders(
      <SEO title="Arena" description="desc" canonicalPath="/arena" />,
    );

    await waitFor(() => {
      const canonical = document.head.querySelector('link[rel="canonical"]');
      expect(canonical).not.toBeNull();
      expect(canonical?.getAttribute("href")).toBe(
        "https://vibe4trading.ai/arena",
      );
    });
  });

  it("noindex mode renders robots meta", async () => {
    renderWithProviders(
      <SEO title="Hidden" description="desc" noindex={true} />,
    );

    await waitFor(() => {
      const robots = getMeta("name", "robots");
      expect(robots).not.toBeNull();
      expect(robots?.getAttribute("content")).toBe("noindex,nofollow");
    });
  });

  it("noindex mode omits canonical link", async () => {
    renderWithProviders(
      <SEO title="Hidden" description="desc" noindex={true} canonicalPath="/test" />,
    );

    await waitFor(() => {
      expect(getMeta("name", "robots")).not.toBeNull();
    });

    const canonical = document.head.querySelector('link[rel="canonical"]');
    expect(canonical).toBeNull();
  });

  it("JSON-LD present on landing page", async () => {
    const { LandingPage } = await import(
      "../src/app/components/landing/LandingPage"
    );

    renderWithProviders(<LandingPage />);

    await waitFor(() => {
      // react-helmet-async may place scripts in head or body depending on jsdom timing
      const jsonLdScripts = document.querySelectorAll(
        'script[type="application/ld+json"]',
      );
      expect(jsonLdScripts.length).toBeGreaterThanOrEqual(2);

      const contents = Array.from(jsonLdScripts).map((s) =>
        JSON.parse(s.textContent || "{}"),
      );
      const types = contents.map((c) => c["@type"]);
      expect(types).toContain("Organization");
      expect(types).toContain("WebApplication");
    });
  });
});
