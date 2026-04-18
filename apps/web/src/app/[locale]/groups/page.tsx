import Link from "next/link";

import type { AppLocale } from "@damah-noshem/shared";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { buildLocaleHref } from "@/lib/api";
import { apiServerFetch } from "@/lib/api-server";
import { getMessages, normalizeLocale } from "@/lib/i18n";

type GroupRecord = {
  access_group_id: string;
  group_name: string;
  group_description: string | null;
  group_status: string;
  last_activity_at: string | null;
};

export default async function GroupsPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string }>;
}>) {
  const { locale: rawLocale } = await params;
  const locale = normalizeLocale(rawLocale) as AppLocale;
  const messages = getMessages(locale);
  const groups = ((await apiServerFetch("/groups")) as GroupRecord[] | null) ?? [];

  return (
    <div className="space-y-6">
      <Card>
        <h1 className="font-display text-3xl font-semibold">{messages.groups}</h1>
      </Card>
      <div className="space-y-3">
        {groups.map((group) => (
          <Link
            key={group.access_group_id}
            href={buildLocaleHref(locale, `/groups/${group.access_group_id}`)}
            className="block"
          >
            <Card className="transition-shadow hover:shadow-md">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-semibold text-lg">{group.group_name}</h2>
                  {group.group_description ? (
                    <p className="mt-1 text-sm text-stone-500">{group.group_description}</p>
                  ) : null}
                  {group.last_activity_at ? (
                    <p className="mt-2 text-xs text-stone-400">
                      {messages.lastActivity}:{" "}
                      {new Date(group.last_activity_at).toLocaleDateString(
                        locale === "he" ? "he-IL" : "en-US",
                      )}
                    </p>
                  ) : null}
                </div>
                <Badge tone={group.group_status === "active" ? "default" : "muted"}>
                  {group.group_status}
                </Badge>
              </div>
            </Card>
          </Link>
        ))}
        {groups.length === 0 ? (
          <Card>
            <p className="text-sm text-stone-500">No groups found.</p>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
