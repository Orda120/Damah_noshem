"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { AppLocale } from "@damah-noshem/shared";

import { apiClientFetch, buildLocaleHref } from "@/lib/api";
import { getMessages } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type LoginResponse = {
  default_language: AppLocale;
};

export function LoginForm({ locale }: Readonly<{ locale: AppLocale }>) {
  const router = useRouter();
  const messages = getMessages(locale);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsPending(true);
    try {
      const response = await apiClientFetch<LoginResponse>("/auth/login/password", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      router.push(buildLocaleHref(response.default_language ?? locale, "/workspaces"));
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Login failed");
    } finally {
      setIsPending(false);
    }
  }

  return (
    <Card className="mx-auto max-w-xl p-8">
      <h1 className="font-display text-3xl font-semibold">{messages.loginTitle}</h1>
      <p className="mt-2 text-sm text-stone-600">Use the seeded demo accounts or your configured local users.</p>
      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <div>
          <label className="mb-2 block text-sm font-medium">{messages.username}</label>
          <Input value={username} onChange={(event) => setUsername(event.target.value)} />
        </div>
        <div>
          <label className="mb-2 block text-sm font-medium">{messages.password}</label>
          <Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </div>
        {error ? <p className="text-sm text-alert">{error}</p> : null}
        <Button disabled={isPending} type="submit" className="w-full">
          {isPending ? "..." : messages.signIn}
        </Button>
      </form>
      <div className="mt-6 rounded-2xl bg-stone-100 p-4 text-sm text-stone-700">
        <p>`admin / admin123`</p>
        <p>`reviewer / reviewer123`</p>
        <p>`submitter / submitter123`</p>
      </div>
    </Card>
  );
}
