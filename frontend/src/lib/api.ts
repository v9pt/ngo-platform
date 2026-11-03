// Server-side calls go straight to the API; the browser uses the /api rewrite.
const API = process.env.API_URL ?? "http://localhost:8000";

export type Scheme = {
  code: string; title_en: string; title_hi: string; need: string;
  districts: string[]; benefit_en: string; benefit_hi: string;
};
export type SchemeDetail = Scheme & {
  summary_hi: string | null;
  who_can_apply_en: string; documents: string[]; how_to_apply_en: string;
  help_centre: string; source_url: string; last_checked: string;
};
export type RuleResult = { field: string; op: string; value: unknown; outcome: "met" | "not_met" | "unknown" };
export type SchemeCheck = {
  code: string; title_en: string; title_hi: string;
  status: "match" | "possible" | "excluded"; rules: RuleResult[];
};

export async function getSchemes(need?: string): Promise<Scheme[] | null> {
  const qs = need ? `?need=${encodeURIComponent(need)}` : "";
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

export type Me = { id: string; email: string; full_name: string; role: string };
export type Campaign = {
  slug: string; title_en: string; title_hi: string; description_en: string; description_hi: string;
  goal_paise: number | null; raised_paise: number;
};
export type Donation = {
  id: string; campaign_slug: string; amount_paise: number; kind: string; status: string;
  gateway_ref: string; receipt_number: string | null;
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

export function rupees(paise: number): string {
  return `₹${new Intl.NumberFormat("en-IN", { minimumFractionDigits: paise % 100 ? 2 : 0 }).format(paise / 100)}`;
}

export type AdminScheme = { code: string; title_en: string; title_hi: string; status: string; notice_text: string; benefit_hi: string };
export type AdminSummary = {
  id: string; scheme_code: string; hindi_text: string; source: string; status: string;
  checks: { needs_attention: boolean; unmatched_numbers?: number[]; devanagari_ok?: boolean; length_ok?: boolean };
};
