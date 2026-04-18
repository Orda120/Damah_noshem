import type { AppLocale } from "@damah-noshem/shared";

import { Card } from "@/components/ui/card";
import { Table } from "@/components/ui/table";
import { GroupCreateForm } from "@/components/group-create-form";
import { apiServerFetch } from "@/lib/api-server";
import { getMessages, normalizeLocale } from "@/lib/i18n";

export default async function GroupsPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string }>;
}>) {
  const { locale: rawLocale } = await params;
  const locale = normalizeLocale(rawLocale) as AppLocale;
  const messages = getMessages(locale);
  const groups = ((await apiServerFetch("/groups")) as Array<Record<string, string>>) ?? [];
  const users = ((await apiServerFetch("/admin/users")) as Array<Record<string, string | string[]>>) ?? [];
  return (
    <div className="space-y-6">
      <Card>
        <h1 className="font-display text-3xl font-semibold">{messages.groups}</h1>
        <p className="mt-2 text-sm text-stone-600">Group creation remains access-code gated and grants immediate group admin membership to the creator.</p>
      </Card>
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <h2 className="mb-4 text-xl font-semibold">Create group</h2>
          <GroupCreateForm />
        </Card>
        <Card>
          <Table
            headers={["Group", "Status", "Description"]}
            rows={groups.map((group) => [group.group_name, group.group_status, group.group_description ?? "-"])}
          />
        </Card>
      </div>
      <Card>
        <h2 className="mb-4 text-xl font-semibold">Available users</h2>
        <Table
          headers={["Name", "Employee", "Roles", "Email"]}
          rows={users.map((user) => [
            locale === "he" ? user.full_name_he : user.full_name_en,
            user.employee_number,
            Array.isArray(user.roles) ? user.roles.join(", ") : String(user.roles),
            user.email,
          ])}
        />
      </Card>
    </div>
  );
}
