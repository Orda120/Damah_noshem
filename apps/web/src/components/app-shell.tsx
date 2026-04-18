"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useEffect, useRef, useState } from "react";

import { clsx } from "clsx";

import type { AppLocale } from "@damah-noshem/shared";

import { LogoutButton } from "@/components/logout-button";
import { buildLocaleHref } from "@/lib/api";
import { getMessages } from "@/lib/i18n";

export function AppShell({
  locale,
  children,
}: Readonly<{ locale: AppLocale; children: React.ReactNode }>) {
  const messages = getMessages(locale);
  const pathname = usePathname();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const navItems = [
    { href: buildLocaleHref(locale, "/groups"), label: messages.groups },
    { href: buildLocaleHref(locale, "/admin/groups"), label: messages.adminGroups },
    { href: buildLocaleHref(locale, "/admin/templates"), label: messages.templates },
    { href: buildLocaleHref(locale, "/admin/users"), label: messages.adminPanel },
  ];

  useEffect(() => {
    setIsDropdownOpen(false);
  }, [pathname]);

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="page-shell min-h-screen">
      <nav className="sticky top-0 z-40 border-b border-black/10 bg-white/80 shadow-sm backdrop-blur">
        <div className="mx-auto flex w-full items-center gap-6 px-8 py-3">
          <Link
            className="font-display text-xl font-semibold text-ink"
            href={buildLocaleHref(locale, "/groups")}
          >
            {messages.appTitle}
          </Link>

          <ul className="flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
              return (
                <li key={item.href}>
                  <Link
                    className={clsx(
                      "rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
                      isActive ? "bg-ink text-white" : "text-ink hover:bg-black/5",
                    )}
                    href={item.href}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>

          <div className={clsx("relative", locale === "he" ? "mr-auto" : "ml-auto")} ref={dropdownRef}>
            <button
              aria-label={messages.settings}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-ink text-base text-white transition hover:bg-ink/80"
              onClick={() => setIsDropdownOpen((value) => !value)}
              type="button"
            >
              &#9776;
            </button>
            {isDropdownOpen ? (
              <div
                className={clsx(
                  "absolute mt-2 w-48 rounded-2xl border border-stone-200 bg-white shadow-lg",
                  locale === "he" ? "left-0" : "right-0",
                )}
              >
                <div className="py-2">
                  <Link
                    className="block px-4 py-2 text-sm text-ink hover:bg-stone-50"
                    href={buildLocaleHref(locale, "/settings")}
                    onClick={() => setIsDropdownOpen(false)}
                  >
                    {messages.languagePreference}
                  </Link>
                </div>
                <div className="border-t border-stone-100 px-3 py-2">
                  <LogoutButton
                    locale={locale}
                    label={messages.logout}
                    className="w-full rounded-xl px-4 py-2 text-start text-sm text-alert hover:bg-red-50"
                  />
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </nav>

      <main className="mx-auto w-full px-8 py-6">{children}</main>
    </div>
  );
}
