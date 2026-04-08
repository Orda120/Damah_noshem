import React from "react";

import type { AppLocale } from "@damah-noshem/shared";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { WorkspaceActionPanel } from "@/components/workspace-action-panel";
import { getMessages } from "@/lib/i18n";

export type WorkspaceDetailRecord = {
  workspace_id: string;
  workspace_title: string;
  workspace_status: string;
  business_date: string | null;
  latest_revision_number: number;
  template: {
    template_name_he: string;
    template_name_en: string;
    field_definitions: Array<{ field_key: string; field_label_he: string; field_label_en: string }>;
  };
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
  clarifications: Array<{ status: string; message: string; line_item_id?: string | null }>;
};

function LifecycleBadge({ status }: Readonly<{ status: string }>) {
  return (
    <Badge tone={status === "done" ? "success" : status === "archived" || status === "closed" ? "muted" : "default"}>
      {status}
    </Badge>
  );
}

export function WorkspaceDetailView({
  locale,
  workspace,
  currentUserRoles,
  actionPanel,
}: Readonly<{
  locale: AppLocale;
  workspace: WorkspaceDetailRecord;
  currentUserRoles: string[];
  actionPanel?: React.ReactNode;
}>) {
  const messages = getMessages(locale);
  const activeItems = workspace.line_items.filter((item) => item.line_item_status !== "archived");
  const archivedItems = workspace.line_items.filter((item) => item.line_item_status === "archived");
  const resolvedActionPanel = actionPanel !== undefined ? actionPanel : (
    <WorkspaceActionPanel
      workspaceId={workspace.workspace_id}
      lineItems={activeItems}
      latestRevisionNumber={workspace.latest_revision_number}
      currentUserRoles={currentUserRoles}
    />
  );

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
              <p className="mt-1 text-sm text-stone-500">
                {workspace.business_date ?? "-"} · revision {workspace.latest_revision_number}
              </p>
            </div>
            <LifecycleBadge status={workspace.workspace_status} />
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between gap-4">
            <h2 className="font-display text-2xl font-semibold">{messages.lineItems}</h2>
            <div className="flex gap-2 text-sm text-stone-500">
              <span>{activeItems.length} active</span>
              <span>{archivedItems.length} archived</span>
            </div>
          </div>
          <div className="mt-4 space-y-4">
            {activeItems.map((item) => (
              <article key={item.line_item_id} className="rounded-[24px] border border-stone-200 bg-stone-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-stone-500">{item.line_item_key}</p>
                    <h3 className="text-lg font-semibold">{item.line_item_title}</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <LifecycleBadge status={item.line_item_status} />
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
                        <div key={`${item.line_item_id}-recommendation-${index}`} className="mb-2 rounded-xl bg-stone-50 p-2 text-sm">
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
                        <div key={`${item.line_item_id}-issue-${index}`} className="mb-2 rounded-xl border border-amber-200 bg-amber-50 p-2 text-sm">
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
                      .filter((clarification) => clarification.line_item_id === item.line_item_id)
                      .map((clarification, index) => (
                        <div key={`${item.line_item_id}-clarification-${index}`} className="mb-2 rounded-xl bg-stone-50 p-2 text-sm">
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

        {archivedItems.length ? (
          <Card>
            <h2 className="font-display text-2xl font-semibold">{messages.archive}</h2>
            <div className="mt-4 space-y-3">
              {archivedItems.map((item) => (
                <div key={item.line_item_id} className="rounded-2xl border border-stone-200 bg-stone-50 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-stone-500">{item.line_item_key}</p>
                      <p className="font-medium">{item.line_item_title}</p>
                    </div>
                    <LifecycleBadge status={item.line_item_status} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        ) : null}

        <Card>
          <h2 className="font-display text-2xl font-semibold">Comments</h2>
          <div className="mt-4 space-y-3">
            {workspace.comments.map((comment, index) => (
              <div key={`${comment.comment_text}-${index}`} className="rounded-2xl border border-stone-200 bg-stone-50 p-3">
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
        {resolvedActionPanel}
      </Card>
    </div>
  );
}
