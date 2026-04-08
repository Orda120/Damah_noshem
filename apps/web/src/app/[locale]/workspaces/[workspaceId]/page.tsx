import type { AppLocale } from "@damah-noshem/shared";

import { Card } from "@/components/ui/card";
import { WorkspaceDetailView, type WorkspaceDetailRecord } from "@/components/workspace-detail-view";
import { apiServerFetch } from "@/lib/api-server";
import { normalizeLocale } from "@/lib/i18n";

type CurrentUserRecord = {
  roles: string[];
};

export default async function WorkspaceDetailPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string; workspaceId: string }>;
}>) {
  const { locale: rawLocale, workspaceId } = await params;
  const locale = normalizeLocale(rawLocale) as AppLocale;
  const workspace = (await apiServerFetch(`/workspaces/${workspaceId}`)) as WorkspaceDetailRecord | null;

  if (!workspace) {
    return <Card>Workspace not found or unauthorized.</Card>;
  }

  const currentUser = (await apiServerFetch("/auth/me")) as CurrentUserRecord | null;
  return (
    <WorkspaceDetailView
      locale={locale}
      workspace={workspace}
      currentUserRoles={currentUser?.roles ?? []}
    />
  );
}
