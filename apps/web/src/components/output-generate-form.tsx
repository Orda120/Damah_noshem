"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiClientFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function OutputGenerateForm() {
  const router = useRouter();
  const [scopeType, setScopeType] = useState("custom");
  const [scopeRef, setScopeRef] = useState("all");

  return (
    <form
      className="flex flex-wrap items-center gap-3"
      onSubmit={async (event) => {
        event.preventDefault();
        await apiClientFetch("/output/generate", {
          method: "POST",
          body: JSON.stringify({ scope_type: scopeType, scope_ref: scopeRef }),
        });
        router.refresh();
      }}
    >
      <select
        className="rounded-full border border-stone-300 bg-white px-4 py-2 text-sm"
        value={scopeType}
        onChange={(event) => setScopeType(event.target.value)}
      >
        <option value="custom">custom</option>
        <option value="group">group</option>
        <option value="business_date">business_date</option>
      </select>
      <Input placeholder="Scope ref" value={scopeRef} onChange={(event) => setScopeRef(event.target.value)} className="max-w-xs" />
      <Button type="submit">Generate</Button>
    </form>
  );
}
