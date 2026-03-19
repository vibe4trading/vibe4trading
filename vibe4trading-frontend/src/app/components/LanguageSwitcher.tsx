import { useTranslation } from "react-i18next";
import { saveLocaleToProfile, setStoredLocale } from "@/i18n/persistence";

export function LanguageSwitcher({ isHome }: { isHome?: boolean }) {
  const { i18n } = useTranslation();
  const currentLang = i18n.language;

  const toggleLanguage = () => {
    const newLang = currentLang === "zh" ? "en" : "zh";
    i18n.changeLanguage(newLang);
    setStoredLocale(newLang);
    saveLocaleToProfile(newLang);
    document.documentElement.lang = newLang;
  };

  const buttonClassName = isHome
    ? "flex h-11 items-center gap-2 border-2 border-white/35 bg-white/8 px-3 text-sm text-white transition hover:bg-white/16 focus-visible:bg-white/16 focus-visible:outline-none"
    : "flex h-11 items-center gap-2 border-2 border-[#555] bg-[#f0f0f0] px-3 text-sm text-[#262626] transition hover:bg-[#e1e8f8] focus-visible:bg-[#e1e8f8] focus-visible:outline-none";

  return (
    <button
      type="button"
      onClick={toggleLanguage}
      className={buttonClassName}
      aria-label="Switch language"
    >
      <span className="text-xs leading-none">{currentLang === "zh" ? "中文" : "EN"}</span>
    </button>
  );
}
