import type { AppLocale } from "@damah-noshem/shared";

import { Card } from "@/components/ui/card";
import { Table } from "@/components/ui/table";
import { OutputGenerateForm } from "@/components/output-generate-form";
import { apiServerFetch } from "@/lib/api-server";
import { getMessages, normalizeLocale } from "@/lib/i18n";

export default async function OutputPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string }>;
}>) {
  const { locale: rawLocale } = await params;
  const locale = normalizeLocale(rawLocale) as AppLocale;
  const messages = getMessages(locale);
  const batches = ((await apiServerFetch("/output/batches")) as Array<Record<string, string>>) ?? [];
  return (
    <div className="space-y-6">
      <Card>
        <h1 className="font-display text-3xl font-semibold">{messages.generateOutput}</h1>
        <p className="mt-2 text-sm text-stone-600">Only done items with current final values are included.</p>
        <div className="mt-4">
          <OutputGenerateForm />
        </div>
      </Card>
      <Card>
        <Table
          headers={["Batch", "Scope", "Included", "Artifact"]}
          rows={batches.map((batch) => [
            batch.output_batch_id,
            `${batch.scope_type} / ${batch.scope_ref}`,
            batch.included_item_count,
            batch.export_artifact_id ?? "-",
          ])}
        />
      </Card>
    </div>
  );
}
