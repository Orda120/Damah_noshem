"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useEffect, useState } from "react";

import { clsx } from "clsx";

import type { AppLocale } from "@damah-noshem/shared";

import { buildLocaleHref } from "@/lib/api";
import { getMessages } from "@/lib/i18n";

export function AppShell({
  locale,
  children,
}: Readonly<{ locale: AppLocale; children: React.ReactNode }>) {
  const messages = getMessages(locale);
  const pathname = usePathname();
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const navItems = [
    { href: buildLocaleHref(locale, "/workspaces"), label: messages.workspaceQueue },
    { href: buildLocaleHref(locale, "/output"), label: messages.output },
    { href: buildLocaleHref(locale, "/archive"), label: messages.archive },
    { href: buildLocaleHref(locale, "/admin/groups"), label: messages.groups },
    { href: buildLocaleHref(locale, "/admin/templates"), label: messages.templates },
    { href: buildLocaleHref(locale, "/admin/users"), label: messages.adminPanel },
  ];

  useEffect(() => {
    setIsNavOpen(false);
    setIsSettingsOpen(false);
  }, [pathname]);

  return (
    <div className="page-shell min-vh-100">
      <nav className="navbar navbar-expand-lg navbar-light border-bottom border-black/10 bg-white/80 shadow-sm backdrop-blur">
        <div className="container-fluid px-4 px-lg-5">
          <Link className="navbar-brand font-display text-xl font-semibold text-ink" href={buildLocaleHref(locale, "/workspaces")}>
            {messages.appTitle}
          </Link>
          <button
            aria-controls="app-navbar-nav"
            aria-expanded={isNavOpen}
            aria-label="Toggle navigation"
            className="navbar-toggler"
            onClick={() => setIsNavOpen((current) => !current)}
            type="button"
          >
            <span className="navbar-toggler-icon" />
          </button>
          <div className={clsx("collapse navbar-collapse", isNavOpen && "show")} id="app-navbar-nav">
            <ul className="navbar-nav me-auto mb-3 mb-lg-0 gap-lg-2">
              {navItems.map((item) => {
                const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
                return (
                  <li className="nav-item" key={item.href}>
                    <Link
                      className={clsx(
                        "nav-link rounded-pill px-3 py-2 text-ink transition-colors",
                        isActive && "bg-ink text-white",
                      )}
                      href={item.href}
                      onClick={() => {
                        setIsNavOpen(false);
                        setIsSettingsOpen(false);
                      }}
                    >
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
            <div className="position-relative">
              <button
                aria-expanded={isSettingsOpen}
                className="btn btn-outline-dark d-inline-flex items-center gap-2 rounded-pill border-0 bg-ink px-4 py-2 text-white"
                onClick={() => setIsSettingsOpen((current) => !current)}
                type="button"
              >
                <span aria-hidden="true" className="text-base leading-none">{"\u2630"}</span>
                <span>{messages.settings}</span>
              </button>
              <div className={clsx("dropdown-menu dropdown-menu-end mt-2 border-0 shadow", isSettingsOpen && "show")}>
                <h6 className="dropdown-header">{messages.settings}</h6>
                <Link
                  className="dropdown-item"
                  href={buildLocaleHref(locale, "/settings#language")}
                  onClick={() => setIsSettingsOpen(false)}
                >
                  {messages.language}
                </Link>
                <Link
                  className="dropdown-item"
                  href={buildLocaleHref(locale, "/settings#logout")}
                  onClick={() => setIsSettingsOpen(false)}
                >
                  {messages.logout}
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>
      <main className="container-fluid min-w-0 px-4 py-6 lg:px-5">{children}</main>
    </div>
  );
}
