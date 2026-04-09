"use client";

import { useRouter } from "next/navigation";

import { clsx } from "clsx";

import type { AppLocale } from "@damah-noshem/shared";

import { apiClientFetch } from "@/lib/api";

export function LogoutButton({
  locale,
  label,
  className,
}: {
  locale: AppLocale;
  label: string;
  className?: string;
}) {
  const router = useRouter();

  async function handleLogout() {
    await apiClientFetch("/auth/logout", { method: "POST" }).catch(() => {});
    router.push(`/${locale}/login`);
  }

  return (
    <button
      onClick={handleLogout}
      className={clsx(className ?? "rounded-full bg-white/10 px-4 py-2 text-sm hover:bg-white/20")}
    >
      {label}
    </button>
  );
}
