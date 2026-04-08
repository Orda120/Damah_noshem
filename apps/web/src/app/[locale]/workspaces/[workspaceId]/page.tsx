import type { AppLocale } from "@damah-noshem/shared";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { WorkspaceActionPanel } from "@/components/workspace-action-panel";
import { apiServerFetch } from "@/lib/api-server";
import { getMessages, normalizeLocale } from "@/lib/i18n";

type WorkspaceDetail = {
  workspace_id: string;
  workspace_title: string;
  workspace_status: string;
  business_date: string | null;
  template: { template_name_he: string; template_name_en: string; field_definitions: Array<{ field_key: string; field_label_he: string; field_label_en: string }> };
  line_items: Array<{
    line_item_id: string;
    line_item_key: string;
    line_item_title: string;
    line_item_status: string;
    recommendations: Array<{ recommended_action: string; reason_text: string | null }>;
    final_values: Array<{ final_value_json: Record<string, unknown>; is_current: boolean }>;
    validation_issues: Array<{ severity: string; message_he: string; message_en: string; status: string }>;
    payloads: Array<{ payload_json: Record<string, unknown> | null; payload_archived: boolean }>;
  }>;
  comments: Array<{ visibility_type: string; comment_text: string }>;
  clarifications: Array<{ status: string; message: string }>;
};

export default async function WorkspaceDetailPage({
  params,
}: Readonly<{
  params: Promise<{ locale: string; workspaceId: string }>;
}>) {
  const { locale: rawLocale, workspaceId } = await params;
  const locale = normalizeLocale(rawLocale) as AppLocale;
  const messages = getMessages(locale);
  const workspace = (await apiServerFetch(`/workspaces/${workspaceId}`)) as WorkspaceDetail | null;

  if (!workspace) {
    return <Card>Workspace not found or unauthorized.</Card>;
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
      <div className="space-y-6">
        <Card>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-stone-500">{messages.workspaceDetail}</p>
              <h1 className="mt-2 font-display text-3xl font-semibold">{workspace.workspace_title}</h1>
              <p className="mt-2 text-sm text-stone-600">
                {workspace.template.template_name_he} / {workspace.template.template_name_en}
              </p>
            </div>
            <Badge tone={workspace.workspace_status === "closed" ? "muted" : "default"}>{workspace.workspace_status}</Badge>
          </div>
        </Card>

        <Card>
          <h2 className="font-display text-2xl font-semibold">{messages.lineItems}</h2>
          <div className="mt-4 space-y-4">
            {workspace.line_items.map((item) => (
              <article key={item.line_item_id} className="rounded-[24px] border border-stone-200 bg-stone-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-stone-500">{item.line_item_key}</p>
                    <h3 className="text-lg font-semibold">{item.line_item_title}</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={item.line_item_status === "done" ? "success" : item.line_item_status === "archived" ? "muted" : "default"}>
                      {item.line_item_status}
                    </Badge>
                    {item.payloads[0]?.payload_archived ? <Badge tone="muted">archived payload</Badge> : null}
                  </div>
                </div>
                <div className="mt-4 grid gap-4 lg:grid-cols-3">
                  <div className="rounded-2xl bg-white p-3">
                    <h4 className="mb-2 text-sm font-semibold">{messages.payload}</h4>
                    <pre className="overflow-auto text-xs text-stone-700">
                      {JSON.stringify(item.payloads[0]?.payload_json ?? {}, null, 2)}
                    </pre>
                  </div>
                  <div className="rounded-2xl bg-white p-3">
                    <h4 className="mb-2 text-sm font-semibold">{messages.recommendations}</h4>
                    {item.recommendations.length ? (
                      item.recommendations.map((recommendation, index) => (
                        <div key={index} className="mb-2 rounded-xl bg-stone-50 p-2 text-sm">
                          <p className="font-medium">{recommendation.recommended_action}</p>
                          <p className="text-stone-600">{recommendation.reason_text ?? "-"}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-stone-500">No recommendation</p>
                    )}
                  </div>
                  <div className="rounded-2xl bg-white p-3">
                    <h4 className="mb-2 text-sm font-semibold">{messages.finalDecision}</h4>
                    {item.final_values.length ? (
                      <pre className="overflow-auto text-xs text-stone-700">
                        {JSON.stringify(item.final_values.find((finalValue) => finalValue.is_current)?.final_value_json ?? {}, null, 2)}
                      </pre>
                    ) : (
                      <p className="text-sm text-stone-500">No final value yet</p>
                    )}
                  </div>
                </div>
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <div className="rounded-2xl bg-white p-3">
                    <h4 className="mb-2 text-sm font-semibold">Validation</h4>
                    {item.validation_issues.length ? (
                      item.validation_issues.map((issue, index) => (
                        <div key={index} className="mb-2 rounded-xl border border-amber-200 bg-amber-50 p-2 text-sm">
                          <p className="font-medium">{issue.severity}</p>
                          <p>{locale === "he" ? issue.message_he : issue.message_en}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-stone-500">No open issues</p>
                    )}
                  </div>
                  <div className="rounded-2xl bg-white p-3">
                    <h4 className="mb-2 text-sm font-semibold">{messages.clarifications}</h4>
                    {workspace.clarifications
                      .filter((clarification) =>
                        workspace.comments.some((comment) => comment.comment_text === clarification.message),
                      )
                      .map((clarification, index) => (
                        <div key={index} className="mb-2 rounded-xl bg-stone-50 p-2 text-sm">
                          <p className="font-medium">{clarification.status}</p>
                          <p>{clarification.message}</p>
                        </div>
                      ))}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="font-display text-2xl font-semibold">Comments</h2>
          <div className="mt-4 space-y-3">
            {workspace.comments.map((comment, index) => (
              <div key={index} className="rounded-2xl border border-stone-200 bg-stone-50 p-3">
                <div className="mb-1 flex items-center gap-2">
                  <Badge tone={comment.visibility_type === "internal_only" ? "danger" : "default"}>
                    {comment.visibility_type}
                  </Badge>
                </div>
                <p className="text-sm text-stone-700">{comment.comment_text}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card className="h-fit">
        <WorkspaceActionPanel workspaceId={workspace.workspace_id} lineItems={workspace.line_items} />
      </Card>
    </div>
  );
}
