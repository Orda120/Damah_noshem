"use client";

import { useRouter } from "next/navigation";

import type { AppLocale } from "@damah-noshem/shared";

import { apiClientFetch } from "@/lib/api";

export function LogoutButton({ locale, label }: { locale: AppLocale; label: string }) {
  const router = useRouter();

  async function handleLogout() {
    await apiClientFetch("/auth/logout", { method: "POST" }).catch(() => {});
    router.push(`/${locale}/login`);
  }

  return (
    <button
      onClick={handleLogout}
      className="rounded-full bg-white/10 px-4 py-2 text-sm hover:bg-white/20"
    >
      {label}
    </button>
  );
}
