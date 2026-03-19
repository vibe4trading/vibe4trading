import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import { getStoredLocale, loadLocaleFromProfile, setStoredLocale } from "./persistence";
import { resources } from "./types";

// Resolve locale synchronously so i18n is ready before React renders.
// Fall back to localStorage → browser language → "en".
function getImmediateLocale(): string {
  const stored = getStoredLocale();
  if (stored) return stored;

  const browserLocale = navigator.language.split("-")[0];
  return ["en", "zh"].includes(browserLocale) ? browserLocale : "en";
}

i18n.use(initReactI18next).init({
  resources,
  lng: getImmediateLocale(),
  fallbackLng: "en",
  defaultNS: "common",
  ns: ['common', 'landing', 'arena', 'runs', 'admin', 'errors'],
  interpolation: {
    escapeValue: false,
  },
});

// After init, check if the server-side profile has a different locale and switch.
loadLocaleFromProfile().then((profileLocale) => {
  if (profileLocale && profileLocale !== i18n.language) {
    i18n.changeLanguage(profileLocale);
    setStoredLocale(profileLocale);
  }
});

export default i18n;
