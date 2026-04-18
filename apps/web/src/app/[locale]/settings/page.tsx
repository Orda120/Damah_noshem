import type { AppLocale } from "@damah-noshem/shared";

import { LanguageSettingsForm } from "@/components/language-settings-form";
import { LogoutButton } from "@/components/logout-button";
import { Card } from "@/components/ui/card";
import { apiServerFetch } from "@/lib/api-server";
import { getMessages, normalizeLocale } from "@/lib/i18n";

type PreferencesRecord = {
  default_language: AppLocale;
};

export default async function SettingsPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string }>;
}>) {
  const { locale: rawLocale } = await params;
  const locale = normalizeLocale(rawLocale) as AppLocale;
  const messages = getMessages(locale);
  const preferences = (await apiServerFetch("/auth/preferences")) as PreferencesRecord | null;

  return (
    <div className="space-y-6">
      <Card>
        <h1 className="font-display text-3xl font-semibold">{messages.settings}</h1>
        <p className="mt-2 text-sm text-stone-600">{messages.settingsDescription}</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <a className="btn btn-outline-dark rounded-pill px-4" href="#language">{messages.language}</a>
          <a className="btn btn-outline-dark rounded-pill px-4" href="#logout">{messages.logout}</a>
        </div>
      </Card>
      <section id="language">
        <LanguageSettingsForm defaultLanguage={preferences?.default_language ?? locale} locale={locale} />
      </section>
      <section id="logout">
        <Card className="max-w-3xl p-8">
          <h2 className="font-display text-2xl font-semibold">{messages.logout}</h2>
          <p className="mt-2 text-sm text-stone-600">{messages.logoutDescription}</p>
          <div className="mt-6">
            <LogoutButton className="btn btn-outline-danger rounded-pill px-4 py-2" locale={locale} label={messages.logout} />
          </div>
        </Card>
      </section>
    </div>
  );
}
