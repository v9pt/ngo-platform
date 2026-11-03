// Server-side calls go straight to the API; the browser uses the /api rewrite.
const API = process.env.API_URL ?? "http://localhost:8000";

export type Scheme = {
  code: string; title_en: string; title_hi: string; need: string;
  districts: string[]; benefit_en: string; benefit_hi: string;
};
export type SchemeDetail = Scheme & {
  summary_hi: string | null;
  who_can_apply_en: string; who_can_apply_hi: string; documents: string[]; documents_hi: string[];
  how_to_apply_en: string; how_to_apply_hi: string; help_centre: string; help_centre_hi: string;
  notice_text: string; source_url: string; last_checked: string;
};
export type RuleResult = { field: string; op: string; value: unknown; outcome: "met" | "not_met" | "unknown" };
export type SchemeCheck = {
  code: string; title_en: string; title_hi: string; need: string; benefit_en: string; benefit_hi: string;
  status: "match" | "possible" | "excluded"; rules: RuleResult[];
};

export async function getSchemes(filter: { need?: string; district?: string } = {}): Promise<Scheme[] | null> {
  const params = new URLSearchParams(Object.entries(filter).filter((e): e is [string, string] => Boolean(e[1])));
  const qs = params.size ? `?${params}` : "";
  try {
    const r = await fetch(`${API}/v1/schemes${qs}`, { cache: "no-store" });
    return r.ok ? ((await r.json()) as Scheme[]) : null;
  } catch {
    return null;
  }
}

export async function getScheme(code: string): Promise<SchemeDetail | null | "error"> {
  try {
    const r = await fetch(`${API}/v1/schemes/${encodeURIComponent(code)}`, { cache: "no-store" });
    if (r.status === 404) return null;
    return r.ok ? ((await r.json()) as SchemeDetail) : "error";
  } catch {
    return "error";
  }
}

import { cookies } from "next/headers";

export type Me = { id: string; email: string; full_name: string; role: string; pan_masked: string | null };
export type Campaign = {
  slug: string; title_en: string; title_hi: string; description_en: string; description_hi: string;
  goal_paise: number | null; raised_paise: number;
};
export type Donation = {
  id: string; campaign_slug: string; campaign_title_en: string; campaign_title_hi: string;
  amount_paise: number; kind: string; status: string; gateway_ref: string;
  receipt_number: string | null; has_80g: boolean; failure_reason: string | null; created_at: string | null;
};
export type Mandate = {
  id: string; campaign_title_en: string; campaign_title_hi: string; amount_paise: number;
  status: string; next_charge_on: string;
};

/** Server-side call that forwards the visitor's session cookie to the API. */
export async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const cookie = (await cookies()).toString();
  return fetch(`${API}${path}`, { ...init, headers: { ...init.headers, cookie }, cache: "no-store" });
}

export async function getMe(): Promise<Me | null> {
  try {
    const r = await authedFetch("/v1/auth/me");
    return r.ok ? ((await r.json()) as Me) : null;
  } catch {
    return null;
  }
}

export async function getCampaigns(): Promise<Campaign[] | null> {
  try {
    const r = await fetch(`${API}/v1/campaigns`, { cache: "no-store" });
    return r.ok ? ((await r.json()) as Campaign[]) : null;
  } catch {
    return null;
  }
}

export { rupees } from "./format";

export type AdminScheme = { code: string; title_en: string; title_hi: string; status: string; notice_text: string; benefit_hi: string };
export type EditableRule = { field: string; op: string; value: unknown };
export type AdminSchemeDetail = AdminScheme & {
  need: string; districts: string[]; benefit_en: string; who_can_apply_en: string; who_can_apply_hi: string;
  documents: string[]; documents_hi: string[]; how_to_apply_en: string; how_to_apply_hi: string;
  help_centre: string; help_centre_hi: string; source_url: string; last_checked: string; rules: EditableRule[];
};
export type AuditEntry = { action: string; actor_name: string | null; detail: Record<string, unknown>; created_at: string };
export type Callback = {
  id: string; phone: string; name: string; scheme_code: string | null; language: string; status: string; created_at: string;
};
export type CampaignReport = {
  slug: string; title_en: string; status: string; goal_paise: number | null; paid_count: number;
  paid_paise: number; pending_count: number; failed_count: number;
};
export type AdminSummary = {
  id: string; scheme_code: string; hindi_text: string; source: string; status: string;
  checks: { needs_attention: boolean; unmatched_numbers?: number[]; devanagari_ok?: boolean; length_ok?: boolean };
};
