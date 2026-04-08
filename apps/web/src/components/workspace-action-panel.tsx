"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiClientFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type LineItemRecord = {
  line_item_id: string;
  line_item_key: string;
  line_item_title: string;
  line_item_status: string;
  payloads: Array<{ payload_json: Record<string, unknown> | null }>;
};

function parseJsonInput(raw: string) {
  return JSON.parse(raw) as Record<string, unknown>;
}

export function WorkspaceActionPanel({
  workspaceId,
  lineItems,
  latestRevisionNumber,
  currentUserRoles,
}: Readonly<{
  workspaceId: string;
  lineItems: LineItemRecord[];
  latestRevisionNumber: number;
  currentUserRoles: string[];
}>) {
  const router = useRouter();
  const [selectedLineItemId, setSelectedLineItemId] = useState(lineItems[0]?.line_item_id ?? "");
  const [revisionNumber, setRevisionNumber] = useState(latestRevisionNumber);
  const selectedLineItem = lineItems.find((item) => item.line_item_id === selectedLineItemId) ?? lineItems[0];
  const [payloadJson, setPayloadJson] = useState(
    JSON.stringify(selectedLineItem?.payloads[0]?.payload_json ?? { reported_amount: 0 }, null, 2),
  );
  const [commentText, setCommentText] = useState("");
  const [clarificationText, setClarificationText] = useState("");
  const [recommendationText, setRecommendationText] = useState(
    JSON.stringify(selectedLineItem?.payloads[0]?.payload_json ?? {}, null, 2),
  );
  const [statusAction, setStatusAction] = useState("done");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!lineItems.length) {
    return <p className="text-sm text-stone-500">No active line items available for editing.</p>;
  }

  const canEditPayload = currentUserRoles.some((role) => ["submitter", "reviewer", "admin"].includes(role));
  const canRequestClarification = currentUserRoles.some((role) => ["reviewer", "admin"].includes(role));
  const canCreateInternalComment = currentUserRoles.some((role) => ["reviewer", "admin"].includes(role));
  const canCreatePublicComment = currentUserRoles.some((role) => ["submitter", "reviewer", "admin"].includes(role));
  const canRecommend = currentUserRoles.some((role) => ["reviewer", "admin"].includes(role));
  const canFinalize = currentUserRoles.includes("admin");

  async function refreshAfter<T>(promise: Promise<T>, onSuccess?: (result: T) => void) {
    setError(null);
    setMessage(null);
    try {
      const result = await promise;
      onSuccess?.(result);
      router.refresh();
      setMessage("Saved");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Request failed");
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="mb-2 block text-sm font-medium">Line item</label>
        <select
          className="w-full rounded-2xl border border-stone-300 bg-white px-4 py-3 text-sm"
          value={selectedLineItemId}
          onChange={(event) => {
            const nextItem = lineItems.find((item) => item.line_item_id === event.target.value);
            setSelectedLineItemId(event.target.value);
            setPayloadJson(JSON.stringify(nextItem?.payloads[0]?.payload_json ?? {}, null, 2));
            setRecommendationText(JSON.stringify(nextItem?.payloads[0]?.payload_json ?? {}, null, 2));
          }}
        >
          {lineItems.map((item) => (
            <option key={item.line_item_id} value={item.line_item_id}>
              {item.line_item_key} - {item.line_item_title}
            </option>
          ))}
        </select>
      </div>

      {canEditPayload ? (
        <section className="space-y-2 rounded-3xl border border-stone-200 bg-stone-50 p-4">
          <h3 className="font-semibold">Payload edit</h3>
          <Textarea value={payloadJson} onChange={(event) => setPayloadJson(event.target.value)} />
          <Button
            onClick={() =>
              refreshAfter(
                apiClientFetch<{ revision_number: number }>(`/workspaces/${workspaceId}/line-items/${selectedLineItemId}/payloads`, {
                  method: "POST",
                  body: JSON.stringify({
                    expected_revision_number: revisionNumber,
                    payload_json: parseJsonInput(payloadJson),
                    revision_reason: currentUserRoles.includes("submitter") ? "submitter_edit" : "admin_edit",
                  }),
                }),
                (result) => setRevisionNumber(result.revision_number),
              )
            }
          >
            Save payload
          </Button>
        </section>
      ) : null}

      {canRequestClarification || canCreateInternalComment || canCreatePublicComment ? (
        <section className="space-y-2 rounded-3xl border border-stone-200 bg-stone-50 p-4">
          <h3 className="font-semibold">Clarification thread</h3>
          {canRequestClarification ? (
            <>
              <Textarea value={clarificationText} onChange={(event) => setClarificationText(event.target.value)} />
              <Button
                variant="secondary"
                onClick={() =>
                  refreshAfter(
                    apiClientFetch(`/workspaces/${workspaceId}/line-items/${selectedLineItemId}/clarifications`, {
                      method: "POST",
                      body: JSON.stringify({ message: clarificationText }),
                    }),
                  )
                }
              >
                Request clarification
              </Button>
            </>
          ) : null}
          <Input placeholder="Comment text" value={commentText} onChange={(event) => setCommentText(event.target.value)} />
          <div className="flex flex-wrap gap-2">
            {canCreatePublicComment ? (
              <Button
                variant="secondary"
                onClick={() =>
                  refreshAfter(
                    apiClientFetch(`/workspaces/${workspaceId}/line-items/${selectedLineItemId}/comments`, {
                      method: "POST",
                      body: JSON.stringify({
                        comment_text: commentText,
                        visibility_type: "submitter_visible",
                      }),
                    }),
                  )
                }
              >
                Add visible comment
              </Button>
            ) : null}
            {canCreateInternalComment ? (
              <Button
                variant="ghost"
                onClick={() =>
                  refreshAfter(
                    apiClientFetch(`/workspaces/${workspaceId}/line-items/${selectedLineItemId}/comments`, {
                      method: "POST",
                      body: JSON.stringify({
                        comment_text: commentText,
                        visibility_type: "internal_only",
                      }),
                    }),
                  )
                }
              >
                Add internal note
              </Button>
            ) : null}
          </div>
        </section>
      ) : null}

      {canRecommend || canFinalize ? (
        <section className="space-y-2 rounded-3xl border border-stone-200 bg-stone-50 p-4">
          <h3 className="font-semibold">Recommendation and final decision</h3>
          <Textarea value={recommendationText} onChange={(event) => setRecommendationText(event.target.value)} />
          <div className="flex flex-wrap gap-2">
            {canRecommend ? (
              <Button
                variant="secondary"
                onClick={() =>
                  refreshAfter(
                    apiClientFetch(`/line-items/${selectedLineItemId}/recommendations`, {
                      method: "POST",
                      body: JSON.stringify({
                        recommended_action: "done",
                        recommended_final_value_json: parseJsonInput(recommendationText),
                      }),
                    }),
                  )
                }
              >
                Save recommendation
              </Button>
            ) : null}
            {canFinalize ? (
              <>
                <select
                  className="rounded-full border border-stone-300 bg-white px-4 py-2 text-sm"
                  value={statusAction}
                  onChange={(event) => setStatusAction(event.target.value)}
                >
                  <option value="done">done</option>
                  <option value="closed">closed</option>
                  <option value="open">reopen</option>
                  <option value="archived">archive</option>
                </select>
                <Button
                  onClick={() =>
                    refreshAfter(
                      apiClientFetch(`/line-items/${selectedLineItemId}/finalize`, {
                        method: "POST",
                        body: JSON.stringify({
                          action: statusAction,
                          final_value_json: parseJsonInput(recommendationText),
                          change_reason: "Updated from workspace detail panel",
                        }),
                      }),
                    )
                  }
                >
                  Apply final action
                </Button>
              </>
            ) : null}
          </div>
        </section>
      ) : null}

      {message ? <p className="text-sm text-accent">{message}</p> : null}
      {error ? <p className="text-sm text-alert">{error}</p> : null}
    </div>
  );
}
