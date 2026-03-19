import { apiJson } from "@/app/lib/v4t";

const LOCALE_STORAGE_KEY = "i18nextLng";

export async function saveLocaleToProfile(locale: string): Promise<void> {
  try {
    await apiJson("/api/me/preferences", {
      method: "PATCH",
      body: { locale },
    });
  } catch {
    // Silently fail - user might not be logged in
  }
}

export async function loadLocaleFromProfile(): Promise<string | null> {
  try {
    const prefs = await apiJson<{ locale?: string }>("/api/me/preferences");
    return prefs.locale || null;
  } catch {
    return null;
  }
}

export function getStoredLocale(): string | null {
  return localStorage.getItem(LOCALE_STORAGE_KEY);
}

export function setStoredLocale(locale: string): void {
  localStorage.setItem(LOCALE_STORAGE_KEY, locale);
}

export async function getPreferredLocale(): Promise<string> {
  const profileLocale = await loadLocaleFromProfile();
  if (profileLocale) return profileLocale;

  const storedLocale = getStoredLocale();
  if (storedLocale) return storedLocale;

  const browserLocale = navigator.language.split("-")[0];
  return ["en", "zh"].includes(browserLocale) ? browserLocale : "en";
}
