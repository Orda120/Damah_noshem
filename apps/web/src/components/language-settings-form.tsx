"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { clsx } from "clsx";

import { locales, type AppLocale } from "@damah-noshem/shared";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { apiClientFetch, buildLocaleHref } from "@/lib/api";
import { getMessages } from "@/lib/i18n";

const languageLabels: Record<AppLocale, string> = {
  he: "עברית",
  en: "English",
};

export function LanguageSettingsForm({
  locale,
  defaultLanguage,
}: Readonly<{
  locale: AppLocale;
  defaultLanguage: AppLocale;
}>) {
  const router = useRouter();
  const messages = getMessages(locale);
  const [selectedLanguage, setSelectedLanguage] = useState(defaultLanguage);
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsPending(true);
    try {
      await apiClientFetch("/auth/preferences", {
        method: "PATCH",
        body: JSON.stringify({ default_language: selectedLanguage }),
      });
      router.replace(buildLocaleHref(selectedLanguage, "/settings"));
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : messages.languageUpdateFailed);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <Card className="max-w-3xl p-8">
      <h2 className="font-display text-2xl font-semibold">{messages.languagePreference}</h2>
      <p className="mt-2 text-sm text-stone-600">{messages.languagePreferenceDescription}</p>
      <form className="mt-6 space-y-5" onSubmit={onSubmit}>
        <fieldset className="space-y-3">
          {locales.map((language) => {
            const isSelected = selectedLanguage === language;
            return (
              <label
                key={language}
                className={clsx(
                  "flex cursor-pointer items-center justify-between rounded-3xl border border-stone-200 bg-white px-5 py-4 transition",
                  isSelected && "border-accent bg-sand/30",
                )}
              >
                <div>
                  <p className="text-base font-medium text-ink">{languageLabels[language]}</p>
                  <p className="mt-1 text-sm text-stone-600">
                    {isSelected ? messages.currentSelection : messages.languageOptionHint}
                  </p>
                </div>
                <input
                  checked={isSelected}
                  className="h-4 w-4 accent-accent"
                  name="default_language"
                  onChange={() => setSelectedLanguage(language)}
                  type="radio"
                  value={language}
                />
              </label>
            );
          })}
        </fieldset>
        {error ? <p className="text-sm text-alert">{error}</p> : null}
        <Button disabled={isPending} type="submit">
          {isPending ? messages.saving : messages.saveChanges}
        </Button>
      </form>
    </Card>
  );
}
