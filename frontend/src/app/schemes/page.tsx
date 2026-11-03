import type { Metadata } from "next";
import Link from "next/link";
import { Empty, LoadFailed } from "@/components/States";
import { getSchemes } from "@/lib/api";
import { DISTRICTS, NEEDS, districtName, needName } from "@/lib/finder";
import { getLang, t } from "@/lib/i18n";

export const metadata: Metadata = { title: "Schemes" };

export default async function Schemes({ searchParams }: { searchParams: Promise<{ need?: string; district?: string }> }) {
  const lang = await getLang();
  const d = t(lang);
  const { need, district } = await searchParams;
  const schemes = await getSchemes({ need, district });
  const link = (n?: string) => {
    const q = new URLSearchParams();
    if (n) q.set("need", n);
    if (district) q.set("district", district);
    return q.size ? `/schemes?${q}` : "/schemes";
  };
  return (
    <section className="wrap page stack">
      <h1>{d.schemes}</h1>
      <nav className="filters" aria-label={d.byNeed}>
        <Link className="chip" href={link()} aria-current={!need ? "true" : undefined}>{d.allNeeds}</Link>
        {NEEDS.map((n) => (
          <Link key={n.value} className="chip" href={link(n.value)} aria-current={need === n.value ? "true" : undefined}>{n[lang]}</Link>
        ))}
      </nav>
      <form method="get" action="/schemes" className="row" style={{ alignItems: "flex-end" }}>
        {need && <input type="hidden" name="need" value={need} />}
        <div className="field" style={{ flex: "1 1 14rem", maxWidth: "22rem" }}>
          <label htmlFor="district">{d.district}</label>
          <select id="district" name="district" defaultValue={district ?? ""}>
            <option value="">{d.allDistricts}</option>
            {DISTRICTS.map((x) => <option key={x} value={x}>{districtName(x, lang)}</option>)}
          </select>
        </div>
        <button type="submit">{d.applyFilter}</button>
      </form>
      {schemes === null ? (
        <LoadFailed text={d.loadError} />
      ) : schemes.length === 0 ? (
        need || district
          ? <Empty text={d.emptyFilter} href="/schemes" action={d.clearFilter} />
          : <Empty text={d.noSchemes} />
      ) : (
        <div>
          {schemes.map((s) => (
            <div key={s.code} className="scheme-row">
              <Link href={`/schemes/${s.code}`}>{lang === "hi" ? s.title_hi : s.title_en}</Link>
              <span className="benefit">{(lang === "hi" && s.benefit_hi) || s.benefit_en}</span>
              <span className="muted">{needName(s.need, lang)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
