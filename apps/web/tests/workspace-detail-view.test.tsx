import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { WorkspaceDetailView, type WorkspaceDetailRecord } from "@/components/workspace-detail-view";

const workspace: WorkspaceDetailRecord = {
  workspace_id: "workspace-1",
  workspace_title: "פיוס יומי 2026-04-08",
  workspace_status: "active",
  business_date: "2026-04-08",
  latest_revision_number: 3,
  template: {
    template_name_he: "פיוס יומי",
    template_name_en: "Daily Reconciliation",
    field_definitions: [],
  },
  line_items: [
    {
      line_item_id: "line-1",
      line_item_key: "LI-001",
      line_item_title: "בדיקת התאמה",
      line_item_status: "open",
      recommendations: [],
      final_values: [],
      validation_issues: [],
      payloads: [{ payload_json: { reported_amount: 1200 }, payload_archived: false }],
    },
    {
      line_item_id: "line-2",
      line_item_key: "LI-002",
      line_item_title: "פריט בארכיון",
      line_item_status: "archived",
      recommendations: [],
      final_values: [],
      validation_issues: [],
      payloads: [{ payload_json: null, payload_archived: true }],
    },
  ],
  comments: [{ visibility_type: "submitter_visible", comment_text: "looks good" }],
  clarifications: [{ status: "open", message: "please explain", line_item_id: "line-1" }],
};

test("workspace detail view renders lifecycle sections and payload data", () => {
  const html = renderToStaticMarkup(
    <WorkspaceDetailView locale="he" workspace={workspace} currentUserRoles={["admin"]} actionPanel={null} />,
  );

  assert.match(html, /פיוס יומי 2026-04-08/);
  assert.match(html, /LI-001/);
  assert.match(html, /archived/);
  assert.match(html, /reported_amount/);
});
