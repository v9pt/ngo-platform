"use server";

import { revalidatePath } from "next/cache";
import { authedFetch } from "@/lib/api";

async function call(path: string, method: string, body?: unknown) {
  const r = await authedFetch(path, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) {
    const p = (await r.json().catch(() => ({}))) as { detail?: string };
    throw new Error(p.detail ?? `Request failed (${r.status})`);
  }
}

export async function transition(formData: FormData) {
  const code = String(formData.get("code"));
  await call(`/v1/admin/schemes/${encodeURIComponent(code)}/transition`, "POST", { to: String(formData.get("to")) });
  revalidatePath("/admin");
  revalidatePath(`/admin/schemes/${code}`);
}

export async function saveNotice(formData: FormData) {
  const code = String(formData.get("code"));
  await call(`/v1/admin/schemes/${encodeURIComponent(code)}`, "PATCH", { notice_text: String(formData.get("notice_text") ?? "") });
  revalidatePath(`/admin/schemes/${code}`);
}

export async function draftSummary(formData: FormData) {
  const code = String(formData.get("code"));
  await call(`/v1/admin/schemes/${encodeURIComponent(code)}/summary-draft`, "POST");
  revalidatePath(`/admin/schemes/${code}`);
}

export async function editSummary(formData: FormData) {
  await call(`/v1/admin/summaries/${encodeURIComponent(String(formData.get("id")))}`, "PATCH", {
    hindi_text: String(formData.get("hindi_text") ?? ""),
  });
  revalidatePath(`/admin/schemes/${String(formData.get("code"))}`);
}

export async function reviewSummary(formData: FormData) {
  const verb = formData.get("verb") === "reject" ? "reject" : "approve";
  await call(`/v1/admin/summaries/${encodeURIComponent(String(formData.get("id")))}/${verb}`, "POST");
  revalidatePath(`/admin/schemes/${String(formData.get("code"))}`);
}
