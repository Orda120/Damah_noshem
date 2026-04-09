import { redirect } from "next/navigation";

import { buildLocaleHref } from "@/lib/api";
import { normalizeLocale } from "@/lib/i18n";

export default async function LocaleRootPage({
  params,
}: Readonly<{ params: Promise<{ locale: string }> }>) {
  const { locale: rawLocale } = await params;
  const locale = normalizeLocale(rawLocale);
  redirect(buildLocaleHref(locale, "/groups"));
}
