"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { authedFetch } from "@/lib/api";

export type ActionResult = { error?: string; note?: string } | null;

async function call(path: string, method: string, body?: unknown): Promise<{ error?: string; data?: unknown }> {
  try {
    const r = await authedFetch(path, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (r.ok) return { data: await r.json().catch(() => null) };
    const p = (await r.json().catch(() => ({}))) as { detail?: unknown };
    return { error: typeof p.detail === "string" ? p.detail : `The server refused this (${r.status}).` };
  } catch {
    return { error: "Could not reach the server. Nothing was saved; try again." };
  }
}

const path = (code: FormDataEntryValue | null) => `/v1/admin/schemes/${encodeURIComponent(String(code))}`;
const lines = (v: FormDataEntryValue | null) => String(v ?? "").split("\n").map((s) => s.trim()).filter(Boolean);

function refresh(code: FormDataEntryValue | null) {
  revalidatePath("/admin");
  revalidatePath(`/admin/schemes/${String(code)}`);
}

export async function transition(_: ActionResult, form: FormData): Promise<ActionResult> {
  const code = form.get("code");
  const out = await call(`${path(code)}/transition`, "POST", { to: String(form.get("to")) });
  if (!out.error) refresh(code);
  return { error: out.error };
}

export async function createScheme(_: ActionResult, form: FormData): Promise<ActionResult> {
  const out = await call("/v1/admin/schemes", "POST", {
    title_en: String(form.get("title_en") ?? ""),
    title_hi: String(form.get("title_hi") ?? ""),
    need: String(form.get("need") ?? ""),
  });
  if (out.error) return { error: out.error.includes("422") ? "Fill in both titles and the need." : out.error };
  redirect(`/admin/schemes/${(out.data as { code: string }).code}`);
}

export async function saveScheme(_: ActionResult, form: FormData): Promise<ActionResult> {
  const code = form.get("code");
  const body: Record<string, unknown> = { documents: lines(form.get("documents")), documents_hi: lines(form.get("documents_hi")), districts: form.getAll("districts").map(String) };
  for (const key of ["title_en", "title_hi", "need", "benefit_en", "benefit_hi", "who_can_apply_en", "who_can_apply_hi", "how_to_apply_en", "how_to_apply_hi", "help_centre", "help_centre_hi", "source_url", "last_checked", "notice_text"]) {
    body[key] = String(form.get(key) ?? "");
  }
  try {
    body.rules = JSON.parse(String(form.get("rules") ?? "[]"));
  } catch {
    return { error: "The rules could not be read. Reload the page and try again." };
  }
  const out = await call(path(code), "PATCH", body);
  if (!out.error) refresh(code);
  return { error: out.error };
}

export async function draftSummary(_: ActionResult, form: FormData): Promise<ActionResult> {
  const code = form.get("code");
  const out = await call(`${path(code)}/summary-draft`, "POST");
  if (out.error) return { error: `${out.error} You can write the summary by hand below.` };
  refresh(code);
  return {};
}

export async function writeSummary(_: ActionResult, form: FormData): Promise<ActionResult> {
  const code = form.get("code");
  const out = await call(`${path(code)}/summaries`, "POST", { hindi_text: String(form.get("hindi_text") ?? "") });
  if (!out.error) refresh(code);
  return { error: out.error };
}

export async function editSummary(_: ActionResult, form: FormData): Promise<ActionResult> {
  const out = await call(`/v1/admin/summaries/${encodeURIComponent(String(form.get("id")))}`, "PATCH", {
    hindi_text: String(form.get("hindi_text") ?? ""),
  });
  if (!out.error) refresh(form.get("code"));
  return { error: out.error };
}

export async function reviewSummary(_: ActionResult, form: FormData): Promise<ActionResult> {
  const verb = form.get("verb") === "reject" ? "reject" : "approve";
  const out = await call(`/v1/admin/summaries/${encodeURIComponent(String(form.get("id")))}/${verb}`, "POST");
  if (!out.error) refresh(form.get("code"));
  return { error: out.error };
}

export async function finishCallback(_: ActionResult, form: FormData): Promise<ActionResult> {
  const out = await call(`/v1/admin/callbacks/${encodeURIComponent(String(form.get("id")))}/done`, "POST");
  if (!out.error) { revalidatePath("/admin/callbacks"); revalidatePath("/admin"); }
  return { error: out.error };
}

export async function runMonthly(): Promise<ActionResult> {
  const out = await call("/v1/admin/mandates/run", "POST");
  if (out.error) return { error: out.error };
  revalidatePath("/admin/reports");
  const { charged } = out.data as { charged: number };
  return { note: charged === 0 ? "Nothing was due today." : `Charged ${charged} monthly gift${charged === 1 ? "" : "s"} and issued the receipts.` };
}
