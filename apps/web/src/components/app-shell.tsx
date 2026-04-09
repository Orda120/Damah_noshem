import Link from "next/link";

import type { AppLocale } from "@damah-noshem/shared";

import { buildLocaleHref } from "@/lib/api";
import { getMessages } from "@/lib/i18n";
import { LogoutButton } from "@/components/logout-button";

export function AppShell({
  locale,
  children,
}: Readonly<{ locale: AppLocale; children: React.ReactNode }>) {
  const messages = getMessages(locale);
  const altLocale: AppLocale = locale === "he" ? "en" : "he";

  return (
    <div className="page-shell min-h-screen">
      <div className="mx-auto flex min-h-screen max-w-[1500px] gap-6 px-4 py-6 lg:px-8">
        <aside className="hidden w-72 shrink-0 rounded-[28px] bg-ink p-6 text-white shadow-card lg:block">
          <div className="mb-8">
            <p className="text-xs uppercase tracking-[0.3em] text-white/60">Internal App</p>
            <h1 className="mt-2 font-display text-3xl font-semibold">{messages.appTitle}</h1>
          </div>
          <nav className="space-y-2 text-sm">
            <Link className="block rounded-2xl px-4 py-3 hover:bg-white/10" href={buildLocaleHref(locale, "/workspaces")}>{messages.workspaceQueue}</Link>
            <Link className="block rounded-2xl px-4 py-3 hover:bg-white/10" href={buildLocaleHref(locale, "/output")}>{messages.output}</Link>
            <Link className="block rounded-2xl px-4 py-3 hover:bg-white/10" href={buildLocaleHref(locale, "/archive")}>{messages.archive}</Link>
            <Link className="block rounded-2xl px-4 py-3 hover:bg-white/10" href={buildLocaleHref(locale, "/admin/groups")}>{messages.groups}</Link>
            <Link className="block rounded-2xl px-4 py-3 hover:bg-white/10" href={buildLocaleHref(locale, "/admin/templates")}>{messages.templates}</Link>
          </nav>
          <div className="mt-auto flex flex-col gap-3 pt-8">
            <Link className="rounded-full bg-white/10 px-4 py-2 text-sm" href={buildLocaleHref(altLocale, "/workspaces")}>
              {messages.languageSwitch}
            </Link>
            <LogoutButton locale={locale} label={messages.logout} />
          </div>
        </aside>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
