export const locales = ["he", "en"] as const;
export type AppLocale = (typeof locales)[number];

export const localeDirection: Record<AppLocale, "rtl" | "ltr"> = {
  he: "rtl",
  en: "ltr",
};

export const lifecycleOrder = ["open", "done", "closed", "archived"] as const;
