"use client";

import { useState } from "react";
import type { SchemeCheck } from "@/lib/api";
import type { Dict, Lang } from "@/lib/i18n";

const DISTRICTS = ["Bhopal", "Sehore", "Vidisha", "Raisen", "Rajgarh", "Indore", "Dewas", "Ujjain", "Narmadapuram"];
const BOOL_FIELDS = [
  "has_bpl_card", "pregnant", "first_child", "shg_member", "has_school_age_girl", "owns_pucca_house",
] as const;
const MARITAL = ["single", "married", "widow", "divorced", "separated"] as const;

export function Finder({ d, lang }: { d: Dict; lang: Lang }) {
  const [results, setResults] = useState<SchemeCheck[] | null>(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {};
    const age = String(f.get("age") ?? "").trim();
    if (age) body.age = Number(age);
    for (const k of ["marital_status", "district"] as const) {
      const v = String(f.get(k) ?? "");
      if (v) body[k] = v;
    }
    for (const k of BOOL_FIELDS) {
      const v = String(f.get(k) ?? "");
      if (v) body[k] = v === "yes";
    }
    setBusy(true);
    setError(false);
    try {
      const r = await fetch("/api/v1/schemes/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(String(r.status));
      setResults((await r.json()) as SchemeCheck[]);
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

  const question = (k: (typeof BOOL_FIELDS)[number]) => d[`q_${k}` as keyof Dict] as string;
  const rank = (k: string) => (d[k as keyof Dict] as string) ?? k;

  return (
    <>
      <form onSubmit={onSubmit} noValidate>
        <div className="field">
          <label htmlFor="age">{d.age}</label>
          <input id="age" name="age" type="number" inputMode="numeric" min={0} max={120} />
        </div>
        <div className="field">
          <label htmlFor="marital_status">{d.maritalStatus}</label>
          <select id="marital_status" name="marital_status" defaultValue="">
            <option value="">{d.notSure}</option>
            {MARITAL.map((m) => (
              <option key={m} value={m}>{d[`marital_${m}` as keyof Dict] as string}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="district">{d.district}</label>
          <select id="district" name="district" defaultValue="">
            <option value="">{d.notSure}</option>
            {DISTRICTS.map((x) => <option key={x} value={x}>{x}</option>)}
          </select>
        </div>
        {BOOL_FIELDS.map((k) => (
          <div className="field" key={k}>
            <label htmlFor={k}>{question(k)}</label>
            <select id={k} name={k} defaultValue="">
              <option value="">{d.notSure}</option>
              <option value="yes">{d.yes}</option>
              <option value="no">{d.no}</option>
            </select>
          </div>
        ))}
        <button type="submit" className="primary" disabled={busy}>{d.check}</button>
      </form>

      <div aria-live="polite">
        {error && <p role="alert">{d.loadError}</p>}
        {results && (
          <section>
            <h2>{d.results}</h2>
            <div className="grid">
              {results.map((r) => (
                <article key={r.code} className="card">
                  <span className={`badge ${r.status}`}>{rank(r.status)}</span>
                  <h3 style={{ margin: "0.5rem 0 0" }}>{lang === "hi" ? r.title_hi : r.title_en}</h3>
                  <ul className="rules">
                    {r.rules.map((x, i) => (
                      <li key={i} className="muted">
                        {x.field.replaceAll("_", " ")} {x.op} {JSON.stringify(x.value)} — {rank(x.outcome)}
                      </li>
                    ))}
                  </ul>
                  <a href={`/schemes/${r.code}`}>{d.schemes} →</a>
                </article>
              ))}
            </div>
          </section>
        )}
      </div>
    </>
  );
}
