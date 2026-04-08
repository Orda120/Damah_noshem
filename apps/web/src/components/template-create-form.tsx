"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiClientFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const defaultFields = JSON.stringify(
  [
    {
      field_key: "reported_amount",
      field_label_he: "סכום מדווח",
      field_label_en: "Reported Amount",
      field_type: "number",
      is_required: true,
      display_order: 1,
    },
  ],
  null,
  2,
);

export function TemplateCreateForm() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [nameHe, setNameHe] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [fieldsJson, setFieldsJson] = useState(defaultFields);

  return (
    <form
      className="space-y-3"
      onSubmit={async (event) => {
        event.preventDefault();
        await apiClientFetch("/templates", {
          method: "POST",
          body: JSON.stringify({
            template_code: code,
            template_name_he: nameHe,
            template_name_en: nameEn,
            template_status: "draft",
            field_definitions: JSON.parse(fieldsJson),
          }),
        });
        router.refresh();
      }}
    >
      <Input placeholder="Template code" value={code} onChange={(event) => setCode(event.target.value)} />
      <Input placeholder="שם תבנית" value={nameHe} onChange={(event) => setNameHe(event.target.value)} />
      <Input placeholder="Template name" value={nameEn} onChange={(event) => setNameEn(event.target.value)} />
      <Textarea value={fieldsJson} onChange={(event) => setFieldsJson(event.target.value)} />
      <Button type="submit">Create template</Button>
    </form>
  );
}
