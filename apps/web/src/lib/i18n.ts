import { localeDirection, type AppLocale } from "@damah-noshem/shared";

import en from "@/locales/en.json";
import he from "@/locales/he.json";

const dictionaries = { en, he } as const;

export function getMessages(locale: AppLocale) {
  return dictionaries[locale];
}

export function getDirection(locale: AppLocale) {
  return localeDirection[locale];
}

export function normalizeLocale(locale: string): AppLocale {
  return locale === "en" ? "en" : "he";
}

export function t(locale: AppLocale, key: keyof typeof he) {
  return dictionaries[locale][key] ?? dictionaries.he[key];
}
