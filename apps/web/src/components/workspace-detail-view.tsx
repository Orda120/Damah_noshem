import React from "react";

import type { AppLocale } from "@damah-noshem/shared";

import { WorkspaceSpreadsheet, type WorkspaceSpreadsheetRecord } from "@/components/workspace-spreadsheet";

// Re-export under the original name so existing imports keep working.
export type WorkspaceDetailRecord = WorkspaceSpreadsheetRecord;

export function WorkspaceDetailView({
  locale,
  workspace,
  currentUserRoles,
  artifactsPanel,
}: Readonly<{
  locale: AppLocale;
  workspace: WorkspaceDetailRecord;
  currentUserRoles: string[];
  actionPanel?: React.ReactNode; // kept for API compat, unused
  artifactsPanel?: React.ReactNode;
}>) {
  return (
    <div className="space-y-6">
      <WorkspaceSpreadsheet locale={locale} workspace={workspace} currentUserRoles={currentUserRoles} />
      {artifactsPanel ? <div>{artifactsPanel}</div> : null}
    </div>
  );
}
