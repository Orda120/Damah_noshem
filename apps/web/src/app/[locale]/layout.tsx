import { AppShell } from "@/components/app-shell";
import { getDirection, getMessages, normalizeLocale } from "@/lib/i18n";

export default async function LocaleLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}>) {
  const { locale: rawLocale } = await params;
  const locale = normalizeLocale(rawLocale);
  const messages = getMessages(locale);
  return (
    <html dir={getDirection(locale)} lang={locale}>
      <body>
        <div className="desktop-unsupported">
          <div className="w-full max-w-lg rounded-[28px] border border-black/10 bg-white/90 p-8 text-center shadow-card backdrop-blur">
            <p className="text-xs uppercase tracking-[0.3em] text-stone-500">{messages.appTitle}</p>
            <h1 className="mt-4 font-display text-3xl font-semibold">{messages.desktopOnlyTitle}</h1>
            <p className="mt-4 text-sm leading-6 text-stone-600">{messages.desktopOnlyBody}</p>
          </div>
        </div>
        <div className="desktop-supported">
          <AppShell locale={locale}>{children}</AppShell>
        </div>
      </body>
    </html>
  );
}
