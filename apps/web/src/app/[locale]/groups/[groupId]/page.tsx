import Link from "next/link";

import type { AppLocale } from "@damah-noshem/shared";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { WorkspaceDetailView, type WorkspaceDetailRecord } from "@/components/workspace-detail-view";
import { buildLocaleHref } from "@/lib/api";
import { apiServerFetch } from "@/lib/api-server";
import { getMessages, normalizeLocale } from "@/lib/i18n";

type GroupRecord = {
  access_group_id: string;
  group_name: string;
  group_description: string | null;
  group_status: string;
};

type WorkspaceSummary = {
  workspace_id: string;
  workspace_title: string;
  business_date: string | null;
  workspace_status: string;
  updated_at: string;
};

type CurrentUserRecord = {
  roles: string[];
};

const ACTIVE_STATUSES = new Set(["draft", "active", "needs_clarification"]);

export default async function GroupDetailPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string; groupId: string }>;
}>) {
  const { locale: rawLocale, groupId } = await params;
  const locale = normalizeLocale(rawLocale) as AppLocale;
  const messages = getMessages(locale);

  const [group, workspaces, currentUser] = await Promise.all([
    apiServerFetch(`/groups/${groupId}`) as Promise<GroupRecord | null>,
    apiServerFetch(`/groups/${groupId}/workspaces`) as Promise<WorkspaceSummary[] | null>,
    apiServerFetch("/auth/me") as Promise<CurrentUserRecord | null>,
  ]);

  if (!group) {
    return <Card>Group not found or unauthorized.</Card>;
  }

  const allWorkspaces = workspaces ?? [];
  const activeWorkspace = allWorkspaces.find((w) => ACTIVE_STATUSES.has(w.workspace_status));
  const archivedWorkspaces = allWorkspaces.filter((w) => !ACTIVE_STATUSES.has(w.workspace_status));

  // Fetch full detail for the active workspace so we can render WorkspaceDetailView
  const activeWorkspaceDetail = activeWorkspace
    ? (apiServerFetch(`/workspaces/${activeWorkspace.workspace_id}`) as Promise<WorkspaceDetailRecord | null>)
    : Promise.resolve(null);
  const workspaceDetail = await activeWorkspaceDetail;

  return (
    <div className="space-y-6">
      {/* Group header */}
      <Card>
        <h1 className="font-display text-3xl font-semibold">{group.group_name}</h1>
        {group.group_description ? (
          <p className="mt-2 text-sm text-stone-600">{group.group_description}</p>
        ) : null}
      </Card>

      {/* Current workflow */}
      <div>
        <h2 className="mb-3 font-display text-xl font-semibold text-stone-700">
          {messages.currentWorkflow}
        </h2>
        {workspaceDetail ? (
          <WorkspaceDetailView
            locale={locale}
            workspace={workspaceDetail}
            currentUserRoles={currentUser?.roles ?? []}
          />
        ) : (
          <Card>
            <p className="text-sm text-stone-500">{messages.noActiveWorkflow}</p>
          </Card>
        )}
      </div>

      {/* Archive */}
      {archivedWorkspaces.length > 0 ? (
        <div>
          <h2 className="mb-3 font-display text-xl font-semibold text-stone-700">
            {messages.archive}
          </h2>
          <Card>
            <div className="space-y-2">
              {archivedWorkspaces.map((w) => (
                <div
                  key={w.workspace_id}
                  className="flex items-center justify-between gap-4 rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3"
                >
                  <div>
                    <p className="font-medium">{w.workspace_title}</p>
                    <p className="text-xs text-stone-500">{w.business_date ?? "-"}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge tone="muted">{w.workspace_status}</Badge>
                    <Link
                      href={buildLocaleHref(locale, `/workspaces/${w.workspace_id}`)}
                      className="text-xs font-medium text-accent hover:underline"
                    >
                      Open
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
