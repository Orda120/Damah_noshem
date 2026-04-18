import type { AppLocale } from "@damah-noshem/shared";

import { ArtifactUploadForm } from "@/components/artifact-upload-form";
import { Card } from "@/components/ui/card";
import { WorkspaceDetailView, type WorkspaceDetailRecord } from "@/components/workspace-detail-view";
import { apiServerFetch } from "@/lib/api-server";
import { normalizeLocale } from "@/lib/i18n";

type CurrentUserRecord = {
  roles: string[];
};

type ArtifactRecord = {
  artifact_id: string;
  artifact_type: string;
  file_name: string;
  mime_type: string;
  link_role: string;
};

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000/api/v1";

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

  const [currentUser, artifacts] = await Promise.all([
    apiServerFetch("/auth/me") as Promise<CurrentUserRecord | null>,
    apiServerFetch(`/artifacts?entity_type=workspace&entity_id=${workspaceId}`) as Promise<ArtifactRecord[] | null>,
  ]);

  const artifactsPanel = (
    <div className="space-y-4">
      <section className="space-y-2 rounded-3xl border border-stone-200 bg-stone-50 p-4">
        <h3 className="font-semibold">Attachments</h3>
        {artifacts && artifacts.length > 0 ? (
          <ul className="space-y-1">
            {artifacts.map((artifact) => (
              <li key={artifact.artifact_id} className="flex items-center justify-between gap-2 text-sm">
                <span className="truncate text-stone-700">{artifact.file_name}</span>
                <a
                  href={`${API_BASE}/artifacts/${artifact.artifact_id}/download`}
                  className="shrink-0 rounded-full bg-stone-100 px-3 py-1 text-xs font-medium hover:bg-stone-200"
                  download={artifact.file_name}
                >
                  Download
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-stone-500">No attachments yet.</p>
        )}
        <div className="pt-2">
          <ArtifactUploadForm entityType="workspace" entityId={workspaceId} />
        </div>
      </section>
    </div>
  );

  return (
    <WorkspaceDetailView
      locale={locale}
      workspace={workspace}
      currentUserRoles={currentUser?.roles ?? []}
      artifactsPanel={artifactsPanel}
    />
  );
}
