"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type ArtifactUploadFormProps = {
  entityType: "workspace" | "line_item";
  entityId: string;
  linkRole?: string;
};

export function ArtifactUploadForm({ entityType, entityId, linkRole = "supporting_document" }: ArtifactUploadFormProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successName, setSuccessName] = useState<string | null>(null);

  async function handleUpload() {
    const file = inputRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    setSuccessName(null);
    try {
      const form = new FormData();
      form.append("entity_type", entityType);
      form.append("entity_id", entityId);
      form.append("link_role", linkRole);
      form.append("file", file);
      const response = await fetch(`${API_BASE}/artifacts/upload`, {
        method: "POST",
        credentials: "include",
        body: form,
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || "Upload failed");
      }
      setSuccessName(file.name);
      if (inputRef.current) inputRef.current.value = "";
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="file"
          aria-label="Upload document file"
          className="flex-1 rounded-2xl border border-stone-300 bg-white px-3 py-2 text-sm file:mr-3 file:rounded-full file:border-0 file:bg-stone-100 file:px-3 file:py-1 file:text-xs file:font-medium"
        />
        <Button onClick={handleUpload} disabled={uploading} variant="secondary">
          {uploading ? "Uploading..." : "Upload"}
        </Button>
      </div>
      {successName ? <p className="text-sm text-accent">Uploaded: {successName}</p> : null}
      {error ? <p className="text-sm text-alert">{error}</p> : null}
    </div>
  );
}
