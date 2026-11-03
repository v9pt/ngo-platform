// Server-side calls go straight to the API; the browser uses the /api rewrite.
const API = process.env.API_URL ?? "http://localhost:8000";

export type Scheme = {
  code: string; title_en: string; title_hi: string; need: string;
  districts: string[]; benefit_en: string; benefit_hi: string;
};
export type SchemeDetail = Scheme & {
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
