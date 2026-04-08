import type { AppLocale } from "@damah-noshem/shared";

import { LoginForm } from "@/components/login-form";
import { normalizeLocale } from "@/lib/i18n";

export default async function LoginPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string }>;
}>) {
  const { locale: rawLocale } = await params;
  const locale = normalizeLocale(rawLocale) as AppLocale;
  return (
    <div className="flex min-h-[80vh] items-center justify-center">
      <LoginForm locale={locale} />
    </div>
  );
}
