import type { AppLocale } from "@damah-noshem/shared";

import { Card } from "@/components/ui/card";
import { Table } from "@/components/ui/table";
import { TemplateCreateForm } from "@/components/template-create-form";
import { apiServerFetch } from "@/lib/api-server";
import { getMessages, normalizeLocale } from "@/lib/i18n";

type TemplateRecord = {
  template_code: string;
  template_name_he: string;
  template_name_en: string;
  template_status: string;
  version_number: number;
  field_definitions: Array<{ field_key: string; field_type: string }>;
};

export default async function TemplatesPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string }>;
}>) {
  const { locale: rawLocale } = await params;
  const locale = normalizeLocale(rawLocale) as AppLocale;
  const messages = getMessages(locale);
  const templates = ((await apiServerFetch("/templates")) as TemplateRecord[]) ?? [];
  return (
    <div className="space-y-6">
      <Card>
        <h1 className="font-display text-3xl font-semibold">{messages.templates}</h1>
        <p className="mt-2 text-sm text-stone-600">Templates live in the database and define field behavior and validation hooks for payload JSON.</p>
      </Card>
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <h2 className="mb-4 text-xl font-semibold">Create template</h2>
          <TemplateCreateForm />
        </Card>
        <Card>
          <Table
            headers={["Code", "Name", "Status", "Version", "Fields"]}
            rows={templates.map((template) => [
              template.template_code,
              locale === "he" ? template.template_name_he : template.template_name_en,
              template.template_status,
              template.version_number,
              template.field_definitions.map((field) => `${field.field_key}:${field.field_type}`).join(", "),
            ])}
          />
        </Card>
      </div>
    </div>
  );
}
