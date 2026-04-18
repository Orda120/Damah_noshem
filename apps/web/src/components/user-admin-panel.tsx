"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { apiClientFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type RoleGrantResult = { user_role_assignment_id: string };

export function UserAdminPanel({
  userId,
  isEnabled,
  isLocked,
}: Readonly<{
  userId: string;
  isEnabled: boolean;
  isLocked: boolean;
}>) {
  const router = useRouter();
  const [roleCode, setRoleCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function patch(body: Record<string, boolean>) {
    setError(null);
    setMessage(null);
    try {
      await apiClientFetch(`/admin/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setMessage("Updated");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    }
  }

  async function grantRole() {
    if (!roleCode.trim()) return;
    setError(null);
    setMessage(null);
    try {
      await apiClientFetch<RoleGrantResult>(`/admin/users/${userId}/roles`, {
        method: "POST",
        body: JSON.stringify({ role_code: roleCode.trim(), scope_type: "global" }),
      });
      setMessage(`Role "${roleCode.trim()}" granted`);
      setRoleCode("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    }
  }

  async function revokeRole() {
    if (!roleCode.trim()) return;
    setError(null);
    setMessage(null);
    try {
      await apiClientFetch(`/admin/users/${userId}/roles/${roleCode.trim()}`, {
        method: "DELETE",
      });
      setMessage(`Role "${roleCode.trim()}" revoked`);
      setRoleCode("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    }
  }

  return (
    <div className="space-y-3 min-w-[220px]">
      <div className="flex flex-wrap gap-2">
        <Button
          variant={isEnabled ? "ghost" : "secondary"}
          onClick={() => patch({ is_enabled: !isEnabled })}
        >
          {isEnabled ? "Disable" : "Enable"}
        </Button>
        <Button
          variant={isLocked ? "secondary" : "ghost"}
          onClick={() => patch({ is_locked: !isLocked })}
        >
          {isLocked ? "Unlock" : "Lock"}
        </Button>
      </div>
      <div className="space-y-1">
        <Input
          placeholder="role code (e.g. reviewer)"
          value={roleCode}
          onChange={(e) => setRoleCode(e.target.value)}
        />
        <div className="flex gap-2">
          <Button variant="secondary" onClick={grantRole}>Grant role</Button>
          <Button variant="ghost" onClick={revokeRole}>Revoke role</Button>
        </div>
      </div>
      {message ? <p className="text-sm text-accent">{message}</p> : null}
      {error ? <p className="text-sm text-alert">{error}</p> : null}
    </div>
  );
}
