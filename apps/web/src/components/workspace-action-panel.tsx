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

export function WorkspaceActionPanel({
  workspaceId,
  lineItems,
}: Readonly<{
  workspaceId: string;
  lineItems: LineItemRecord[];
}>) {
  const router = useRouter();
  const [selectedLineItemId, setSelectedLineItemId] = useState(lineItems[0]?.line_item_id ?? "");
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

  async function refreshAfter<T>(promise: Promise<T>) {
    await promise;
    router.refresh();
    setMessage("Saved");
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

      <section className="space-y-2 rounded-3xl border border-stone-200 bg-stone-50 p-4">
        <h3 className="font-semibold">Payload edit</h3>
        <Textarea value={payloadJson} onChange={(event) => setPayloadJson(event.target.value)} />
        <Button
          onClick={() =>
            refreshAfter(
              apiClientFetch(`/workspaces/${workspaceId}/line-items/${selectedLineItemId}/payloads`, {
                method: "POST",
                body: JSON.stringify({
                  expected_revision_number: 0,
                  payload_json: JSON.parse(payloadJson),
                  revision_reason: "admin_edit",
                }),
              }),
            )
          }
        >
          Save payload
        </Button>
      </section>

      <section className="space-y-2 rounded-3xl border border-stone-200 bg-stone-50 p-4">
        <h3 className="font-semibold">Clarification thread</h3>
        <Textarea value={clarificationText} onChange={(event) => setClarificationText(event.target.value)} />
        <div className="flex gap-2">
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
        </div>
        <Input placeholder="Comment text" value={commentText} onChange={(event) => setCommentText(event.target.value)} />
      </section>

      <section className="space-y-2 rounded-3xl border border-stone-200 bg-stone-50 p-4">
        <h3 className="font-semibold">Recommendation and final decision</h3>
        <Textarea value={recommendationText} onChange={(event) => setRecommendationText(event.target.value)} />
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() =>
              refreshAfter(
                apiClientFetch(`/line-items/${selectedLineItemId}/recommendations`, {
                  method: "POST",
                  body: JSON.stringify({
                    recommended_action: "done",
                    recommended_final_value_json: JSON.parse(recommendationText),
                  }),
                }),
              )
            }
          >
            Save recommendation
          </Button>
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
                    final_value_json: JSON.parse(recommendationText),
                    change_reason: "Updated from workspace detail panel",
                  }),
                }),
              )
            }
          >
            Apply final action
          </Button>
        </div>
      </section>

      {message ? <p className="text-sm text-accent">{message}</p> : null}
    </div>
  );
}
