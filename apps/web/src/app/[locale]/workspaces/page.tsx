import Link from "next/link";

import type { AppLocale } from "@damah-noshem/shared";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Table } from "@/components/ui/table";
import { buildLocaleHref } from "@/lib/api";
import { apiServerFetch } from "@/lib/api-server";
import { getMessages, normalizeLocale } from "@/lib/i18n";

export default async function WorkspacesPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string }>;
}>) {
  const { locale: rawLocale } = await params;
  const locale = normalizeLocale(rawLocale) as AppLocale;
  const messages = getMessages(locale);
  const workspaces = ((await apiServerFetch("/workspaces")) as Array<Record<string, string>>) ?? [];

  return (
    <div className="space-y-6">
      <Card>
        <h1 className="font-display text-3xl font-semibold">{messages.workspaceQueue}</h1>
        <p className="mt-2 text-sm text-stone-600">Lifecycle is always visible, even when the template does not expose it as a column.</p>
      </Card>
      <Card>
        <Table
          headers={["Title", "Business date", "Status", "Open"]}
          rows={workspaces.map((workspace) => [
            workspace.workspace_title,
            workspace.business_date ?? "-",
            <Badge
              key={`${workspace.workspace_id}-status`}
              tone={workspace.workspace_status === "done" ? "success" : workspace.workspace_status === "archived" ? "muted" : "default"}
            >
              {workspace.workspace_status}
            </Badge>,
            <Link
              key={`${workspace.workspace_id}-open`}
              className="font-medium text-accent"
              href={buildLocaleHref(locale, `/workspaces/${workspace.workspace_id}`)}
            >
              Open
            </Link>,
          ])}
        />
      </Card>
    </div>
  );
}
