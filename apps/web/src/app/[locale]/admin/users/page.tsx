import type { AppLocale } from "@damah-noshem/shared";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { UserAdminPanel } from "@/components/user-admin-panel";
import { apiServerFetch } from "@/lib/api-server";
import { normalizeLocale } from "@/lib/i18n";

type UserRecord = {
  app_user_id: string;
  employee_number: string;
  full_name_he: string;
  full_name_en: string;
  email: string;
  roles: string[];
  is_enabled: boolean;
  is_locked: boolean;
  default_language: string;
};

export default async function AdminUsersPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string }>;
}>) {
  const { locale: rawLocale } = await params;
  const locale = normalizeLocale(rawLocale) as AppLocale;
  const users = ((await apiServerFetch("/admin/users")) as UserRecord[] | null) ?? [];

  return (
    <div className="space-y-6">
      <Card>
        <h1 className="font-display text-3xl font-semibold">User management</h1>
        <p className="mt-2 text-sm text-stone-600">Enable/disable users, lock accounts, and manage role assignments.</p>
      </Card>
      <div className="space-y-4">
        {users.map((user) => (
          <Card key={user.app_user_id}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="font-semibold">{locale === "he" ? user.full_name_he : user.full_name_en}</p>
                <p className="text-sm text-stone-500">{user.email} · {user.employee_number}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {user.roles.map((role) => (
                    <Badge key={role} tone="default">{role}</Badge>
                  ))}
                  {!user.is_enabled ? <Badge tone="danger">disabled</Badge> : null}
                  {user.is_locked ? <Badge tone="danger">locked</Badge> : null}
                </div>
              </div>
              <UserAdminPanel userId={user.app_user_id} isEnabled={user.is_enabled} isLocked={user.is_locked} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
