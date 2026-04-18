"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiClientFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export function GroupCreateForm() {
  const router = useRouter();
  const [groupName, setGroupName] = useState("");
  const [groupDescription, setGroupDescription] = useState("");
  const [accessCode, setAccessCode] = useState("seed-group-code");

  return (
    <form
      className="space-y-3"
      onSubmit={async (event) => {
        event.preventDefault();
        await apiClientFetch("/groups", {
          method: "POST",
          body: JSON.stringify({ group_name: groupName, group_description: groupDescription, access_code: accessCode }),
        });
        router.refresh();
      }}
    >
      <Input placeholder="Group name" value={groupName} onChange={(event) => setGroupName(event.target.value)} />
      <Textarea placeholder="Description" value={groupDescription} onChange={(event) => setGroupDescription(event.target.value)} />
      <Input placeholder="Access code" value={accessCode} onChange={(event) => setAccessCode(event.target.value)} />
      <Button type="submit">Create group</Button>
    </form>
  );
}
