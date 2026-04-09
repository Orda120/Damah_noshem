"use client";

import React, { useEffect, useState } from "react";

import { useRouter } from "next/navigation";

import type { AppLocale } from "@damah-noshem/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { apiClientFetch } from "@/lib/api";
import { getMessages } from "@/lib/i18n";

// ─── Types ────────────────────────────────────────────────────────────────────

export type FieldDefinition = {
  field_key: string;
  field_label_he: string;
  field_label_en: string;
  field_type: string;
  lock_on_done: boolean;
  lock_on_closed: boolean;
  submitter_editable: boolean;
  reviewer_editable: boolean;
  admin_editable: boolean;
  display_order: number;
};

type LineItemRecord = {
  line_item_id: string;
  line_item_key: string;
  line_item_title: string;
  line_item_status: string;
  closed_reason: string | null;
  payloads: Array<{
    current_payload_id: string;
    payload_json: Record<string, unknown> | null;
    payload_archived: boolean;
    is_current: boolean;
  }>;
  recommendations: Array<{
    recommendation_id: string;
    recommended_action: string;
    recommended_final_value_json: Record<string, unknown> | null;
    reason_text: string | null;
    superseded_at: string | null;
  }>;
  final_values: Array<{
    final_value_id: string;
    final_value_json: Record<string, unknown>;
    is_current: boolean;
  }>;
  validation_issues: Array<{
    validation_issue_id: string;
    severity: string;
    rule_code: string | null;
    message_he: string;
    message_en: string;
    status: string;
  }>;
};

export type WorkspaceSpreadsheetRecord = {
  workspace_id: string;
  workspace_title: string;
  workspace_status: string;
  business_date: string | null;
  latest_revision_number: number;
  access_group_id: string;
  template: {
    template_name_he: string;
    template_name_en: string;
    field_definitions: FieldDefinition[];
  };
  line_items: LineItemRecord[];
  comments: Array<{
    comment_id: string;
    line_item_id: string | null;
    visibility_type: string;
    comment_text: string;
    created_at: string;
  }>;
  clarifications: Array<{
    clarification_request_id: string;
    line_item_id: string | null;
    status: string;
    message: string;
    created_at: string;
  }>;
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function statusTone(status: string): "default" | "success" | "muted" | "danger" {
  if (status === "done") return "success";
  if (status === "closed" || status === "archived") return "muted";
  return "default";
}

function getPayload(item: LineItemRecord): Record<string, unknown> {
  return item.payloads.find((p) => p.is_current)?.payload_json ?? item.payloads[0]?.payload_json ?? {};
}

function getFinalValue(item: LineItemRecord): Record<string, unknown> | null {
  return item.final_values.find((fv) => fv.is_current)?.final_value_json ?? null;
}

function displayCellValue(item: LineItemRecord, fieldKey: string): string {
  const isDone = item.line_item_status === "done";
  const source = isDone ? (getFinalValue(item) ?? getPayload(item)) : getPayload(item);
  const v = source[fieldKey];
  return v !== undefined && v !== null ? String(v) : "";
}

function isCellLocked(item: LineItemRecord, field: FieldDefinition, roles: string[]): boolean {
  if (item.line_item_status === "closed" || item.line_item_status === "archived") return true;
  if (item.line_item_status === "done" && field.lock_on_done) return true;
  return !(
    (roles.includes("submitter") && field.submitter_editable) ||
    (roles.includes("reviewer") && field.reviewer_editable) ||
    (roles.includes("admin") && field.admin_editable)
  );
}

function blockingIssueCount(item: LineItemRecord): number {
  return item.validation_issues.filter((i) => i.severity === "blocking" && i.status === "open").length;
}

function inputTypeFor(fieldType: string): string {
  if (fieldType === "number") return "number";
  if (fieldType === "date") return "date";
  return "text";
}

function safeJson(raw: string): Record<string, unknown> {
  try {
    return JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return {};
  }
}

// ─── Component ────────────────────────────────────────────────────────────────

export function WorkspaceSpreadsheet({
  locale,
  workspace,
  currentUserRoles,
}: Readonly<{
  locale: AppLocale;
  workspace: WorkspaceSpreadsheetRecord;
  currentUserRoles: string[];
}>) {
  const router = useRouter();
  const messages = getMessages(locale);

  const [revisionNumber, setRevisionNumber] = useState(workspace.latest_revision_number);
  useEffect(() => {
    setRevisionNumber(workspace.latest_revision_number);
  }, [workspace.latest_revision_number]);

  const [selectedRowId, setSelectedRowId] = useState<string | null>(null);
  const [editingCell, setEditingCell] = useState<{ rowId: string; fieldKey: string } | null>(null);
  const [editingValue, setEditingValue] = useState("");

  const [clarificationText, setClarificationText] = useState("");
  const [commentText, setCommentText] = useState("");
  const [recommendationJson, setRecommendationJson] = useState("{}");
  const [finalizeAction, setFinalizeAction] = useState("done");
  const [finalValueJson, setFinalValueJson] = useState("{}");
  const [sidebarMsg, setSidebarMsg] = useState<string | null>(null);
  const [sidebarErr, setSidebarErr] = useState<string | null>(null);

  const sortedFields = [...workspace.template.field_definitions].sort((a, b) => a.display_order - b.display_order);
  const selectedItem = workspace.line_items.find((i) => i.line_item_id === selectedRowId) ?? null;

  const canRequestClarification = currentUserRoles.some((r) => ["reviewer", "admin"].includes(r));
  const canComment = currentUserRoles.length > 0;
  const canInternalComment = currentUserRoles.some((r) => ["reviewer", "admin"].includes(r));
  const canRecommend = currentUserRoles.some((r) => ["reviewer", "admin"].includes(r));
  const canFinalize = currentUserRoles.includes("admin");

  async function withFeedback<T>(p: Promise<T>, onSuccess?: (r: T) => void) {
    setSidebarErr(null);
    setSidebarMsg(null);
    try {
      const result = await p;
      onSuccess?.(result);
      router.refresh();
      setSidebarMsg("Saved");
    } catch (e) {
      setSidebarErr(e instanceof Error ? e.message : "Request failed");
    }
  }

  function selectRow(itemId: string) {
    if (selectedRowId === itemId) {
      setSelectedRowId(null);
      return;
    }
    const item = workspace.line_items.find((i) => i.line_item_id === itemId);
    if (!item) return;
    setSelectedRowId(itemId);
    const payload = getPayload(item);
    const fv = getFinalValue(item);
    const defaultJson = JSON.stringify(fv ?? payload, null, 2);
    setRecommendationJson(defaultJson);
    setFinalValueJson(defaultJson);
    setSidebarMsg(null);
    setSidebarErr(null);
  }

  async function saveCell(item: LineItemRecord, fieldKey: string, rawValue: string) {
    const field = sortedFields.find((f) => f.field_key === fieldKey);
    const payload = { ...getPayload(item) };
    if (field?.field_type === "number") {
      payload[fieldKey] = rawValue === "" ? null : Number(rawValue);
    } else {
      payload[fieldKey] = rawValue;
    }
    try {
      const result = await apiClientFetch<{ revision_number: number }>(
        `/workspaces/${workspace.workspace_id}/line-items/${item.line_item_id}/payloads`,
        {
          method: "POST",
          body: JSON.stringify({
            expected_revision_number: revisionNumber,
            payload_json: payload,
            revision_reason: currentUserRoles.includes("submitter") ? "submitter_edit" : "admin_edit",
          }),
        },
      );
      setRevisionNumber(result.revision_number);
      router.refresh();
    } catch {
      // silent — retry on next edit
    }
  }

  return (
    <div className="flex min-h-0 gap-4" style={{ direction: "ltr" }}>
      {/* ── LEFT SIDEBAR ─────────────────────────────────────────────────── */}
      <aside className="flex w-64 shrink-0 flex-col gap-4 border-e border-stone-200 pe-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-stone-400">{messages.workspaceDetail}</p>
          <h2 className="mt-1 font-display text-lg font-semibold leading-tight">{workspace.workspace_title}</h2>
          <p className="mt-1 text-xs text-stone-500">
            {workspace.business_date ?? "–"} · rev {revisionNumber}
          </p>
          <div className="mt-2">
            <Badge tone={statusTone(workspace.workspace_status)}>{workspace.workspace_status}</Badge>
          </div>
        </div>

        {canFinalize ? (
          <Button
            variant="secondary"
            className="w-full"
            onClick={() =>
              withFeedback(
                apiClientFetch(`/output/generate`, {
                  method: "POST",
                  body: JSON.stringify({ scope_type: "group", scope_ref: workspace.access_group_id }),
                }),
              )
            }
          >
            {messages.exportWorkflow}
          </Button>
        ) : null}

        <hr className="border-stone-200" />

        {selectedItem ? (
          <div className="flex flex-col gap-3">
            <div>
              <p className="text-xs uppercase tracking-widest text-stone-400">{messages.rowActions}</p>
              <p className="mt-0.5 text-sm font-semibold">
                {selectedItem.line_item_key} — {selectedItem.line_item_title}
              </p>
            </div>

            {canRequestClarification ? (
              <div className="space-y-2 rounded-2xl border border-stone-200 bg-stone-50 p-3">
                <p className="text-xs font-semibold text-stone-600">{messages.clarifications}</p>
                <textarea
                  rows={2}
                  className="w-full rounded-xl border border-stone-300 bg-white px-3 py-2 text-xs"
                  value={clarificationText}
                  onChange={(e) => setClarificationText(e.target.value)}
                  placeholder="..."
                />
                <Button
                  variant="secondary"
                  className="w-full text-xs"
                  onClick={() =>
                    withFeedback(
                      apiClientFetch(
                        `/workspaces/${workspace.workspace_id}/line-items/${selectedItem.line_item_id}/clarifications`,
                        { method: "POST", body: JSON.stringify({ message: clarificationText }) },
                      ),
                    )
                  }
                >
                  Request clarification
                </Button>
              </div>
            ) : null}

            {canComment ? (
              <div className="space-y-2 rounded-2xl border border-stone-200 bg-stone-50 p-3">
                <p className="text-xs font-semibold text-stone-600">Comment</p>
                <input
                  className="w-full rounded-xl border border-stone-300 bg-white px-3 py-2 text-xs"
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  placeholder="..."
                />
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    className="flex-1 text-xs"
                    onClick={() =>
                      withFeedback(
                        apiClientFetch(
                          `/workspaces/${workspace.workspace_id}/line-items/${selectedItem.line_item_id}/comments`,
                          {
                            method: "POST",
                            body: JSON.stringify({ comment_text: commentText, visibility_type: "submitter_visible" }),
                          },
                        ),
                      )
                    }
                  >
                    Add comment
                  </Button>
                  {canInternalComment ? (
                    <Button
                      variant="ghost"
                      className="flex-1 text-xs"
                      onClick={() =>
                        withFeedback(
                          apiClientFetch(
                            `/workspaces/${workspace.workspace_id}/line-items/${selectedItem.line_item_id}/comments`,
                            {
                              method: "POST",
                              body: JSON.stringify({ comment_text: commentText, visibility_type: "internal_only" }),
                            },
                          ),
                        )
                      }
                    >
                      Internal
                    </Button>
                  ) : null}
                </div>
              </div>
            ) : null}

            {canRecommend && !canFinalize ? (
              <div className="space-y-2 rounded-2xl border border-stone-200 bg-stone-50 p-3">
                <p className="text-xs font-semibold text-stone-600">{messages.recommendations}</p>
                <textarea
                  rows={3}
                  className="w-full rounded-xl border border-stone-300 bg-white px-3 py-2 font-mono text-xs"
                  value={recommendationJson}
                  onChange={(e) => setRecommendationJson(e.target.value)}
                />
                <Button
                  variant="secondary"
                  className="w-full text-xs"
                  onClick={() =>
                    withFeedback(
                      apiClientFetch(`/line-items/${selectedItem.line_item_id}/recommendations`, {
                        method: "POST",
                        body: JSON.stringify({
                          recommended_action: "done",
                          recommended_final_value_json: safeJson(recommendationJson),
                        }),
                      }),
                    )
                  }
                >
                  Save recommendation
                </Button>
              </div>
            ) : null}

            {canFinalize ? (
              <div className="space-y-2 rounded-2xl border border-stone-200 bg-stone-50 p-3">
                <p className="text-xs font-semibold text-stone-600">{messages.finalDecision}</p>
                <textarea
                  rows={3}
                  className="w-full rounded-xl border border-stone-300 bg-white px-3 py-2 font-mono text-xs"
                  value={finalValueJson}
                  onChange={(e) => setFinalValueJson(e.target.value)}
                />
                <div className="flex items-center gap-2">
                  <select
                    aria-label="Action"
                    className="flex-1 rounded-full border border-stone-300 bg-white px-3 py-1.5 text-xs"
                    value={finalizeAction}
                    onChange={(e) => setFinalizeAction(e.target.value)}
                  >
                    <option value="done">done</option>
                    <option value="closed">closed</option>
                    <option value="open">reopen</option>
                    <option value="archived">archive</option>
                  </select>
                  <Button
                    className="flex-1 text-xs"
                    onClick={() =>
                      withFeedback(
                        apiClientFetch(`/line-items/${selectedItem.line_item_id}/finalize`, {
                          method: "POST",
                          body: JSON.stringify({
                            action: finalizeAction,
                            final_value_json: safeJson(finalValueJson),
                            change_reason: "Updated from workflow",
                          }),
                        }),
                      )
                    }
                  >
                    Apply
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-stone-400">{messages.selectRowToAct}</p>
        )}

        {sidebarMsg ? <p className="text-sm text-emerald-600">{sidebarMsg}</p> : null}
        {sidebarErr ? <p className="text-sm text-rose-600">{sidebarErr}</p> : null}
      </aside>

      {/* ── RIGHT SPREADSHEET ────────────────────────────────────────────── */}
      <div className="min-w-0 flex-1 overflow-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b-2 border-stone-200 bg-stone-50">
              <th className="whitespace-nowrap px-3 py-2 text-start text-xs font-semibold text-stone-500">#</th>
              <th className="min-w-[160px] whitespace-nowrap px-3 py-2 text-start text-xs font-semibold text-stone-500">
                Title
              </th>
              {sortedFields.map((field) => (
                <th
                  key={field.field_key}
                  className="min-w-[120px] whitespace-nowrap px-3 py-2 text-start text-xs font-semibold text-stone-500"
                >
                  {locale === "he" ? field.field_label_he : field.field_label_en}
                </th>
              ))}
              <th className="whitespace-nowrap px-3 py-2 text-start text-xs font-semibold text-stone-500">Status</th>
              <th className="whitespace-nowrap px-3 py-2 text-start text-xs font-semibold text-stone-500">Issues</th>
            </tr>
          </thead>
          <tbody>
            {workspace.line_items.map((item) => {
              const isSelected = item.line_item_id === selectedRowId;
              const isDone = item.line_item_status === "done";
              const fv = getFinalValue(item);
              const blockCount = blockingIssueCount(item);

              return (
                <tr
                  key={item.line_item_id}
                  className={`cursor-pointer border-b border-stone-100 transition-colors ${
                    isSelected ? "bg-accent/5" : "hover:bg-stone-50"
                  }`}
                  onClick={() => selectRow(item.line_item_id)}
                >
                  <td className="px-3 py-2 font-mono text-xs text-stone-400">{item.line_item_key}</td>
                  <td className="px-3 py-2 font-medium text-stone-800">{item.line_item_title}</td>

                  {sortedFields.map((field) => {
                    const isEditing =
                      editingCell?.rowId === item.line_item_id && editingCell?.fieldKey === field.field_key;
                    const locked = field.field_type === "file" || isCellLocked(item, field, currentUserRoles);
                    const cellDisplay = isEditing
                      ? editingValue
                      : isDone && fv
                        ? (() => {
                            const v = fv[field.field_key];
                            return v !== undefined && v !== null ? String(v) : "";
                          })()
                        : displayCellValue(item, field.field_key);

                    if (isEditing && !locked) {
                      return (
                        <td key={field.field_key} className="px-1 py-1">
                          <input
                            autoFocus
                            type={inputTypeFor(field.field_type)}
                            value={editingValue}
                            onChange={(e) => setEditingValue(e.target.value)}
                            onBlur={async () => {
                              setEditingCell(null);
                              await saveCell(item, field.field_key, editingValue);
                            }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                setEditingCell(null);
                                void saveCell(item, field.field_key, editingValue);
                              }
                              if (e.key === "Escape") {
                                setEditingCell(null);
                              }
                            }}
                            className="w-full rounded border border-accent px-2 py-1 text-sm outline-none"
                            style={{ minWidth: 100 }}
                          />
                        </td>
                      );
                    }

                    return (
                      <td
                        key={field.field_key}
                        className={[
                          "px-3 py-2",
                          !locked ? "cursor-text hover:bg-accent/5" : "cursor-default",
                          isDone && fv ? "text-emerald-700" : "text-stone-700",
                          blockCount > 0 ? "border border-rose-100 bg-rose-50/30" : "",
                        ]
                          .filter(Boolean)
                          .join(" ")}
                        onClick={(e) => {
                          if (locked) return;
                          e.stopPropagation();
                          setEditingValue(displayCellValue(item, field.field_key));
                          setEditingCell({ rowId: item.line_item_id, fieldKey: field.field_key });
                        }}
                      >
                        {cellDisplay || <span className="text-stone-300">—</span>}
                      </td>
                    );
                  })}

                  <td className="px-3 py-2">
                    <Badge tone={statusTone(item.line_item_status)}>{item.line_item_status}</Badge>
                  </td>
                  <td className="px-3 py-2">
                    {blockCount > 0 ? (
                      <Badge tone="danger">{blockCount}</Badge>
                    ) : (
                      <span className="text-xs text-stone-300">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {workspace.line_items.length === 0 ? (
          <p className="py-10 text-center text-sm text-stone-400">No line items</p>
        ) : null}
      </div>
    </div>
  );
}
