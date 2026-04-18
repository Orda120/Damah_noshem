import type { AppLocale } from "@damah-noshem/shared";

import { Card } from "@/components/ui/card";
import { Table } from "@/components/ui/table";
import { apiServerFetch } from "@/lib/api-server";
import { getMessages, normalizeLocale } from "@/lib/i18n";

export default async function ArchivePage({
  params,
}: Readonly<{
  params: Promise<{ locale: string }>;
}>) {
  const { locale: rawLocale } = await params;
  const locale = normalizeLocale(rawLocale) as AppLocale;
  const messages = getMessages(locale);
  const rows = ((await apiServerFetch("/archive/search")) as Array<Record<string, string>>) ?? [];
  return (
    <div className="space-y-6">
      <Card>
        <h1 className="font-display text-3xl font-semibold">{messages.archiveSearch}</h1>
        <p className="mt-2 text-sm text-stone-600">Archive catalog stays metadata-only; payload retrieval flows through the hot stub row and linked artifact.</p>
      </Card>
      <Card>
        <Table
          headers={["Archive entry", "Workspace", "Line item", "Artifact type", "Archived at"]}
          rows={rows.map((row) => [
            row.archive_catalog_entry_id,
            row.workspace_id ?? "-",
            row.line_item_id ?? "-",
            row.artifact_type,
            row.archived_at,
          ])}
        />
      </Card>
    </div>
  );
}
