import Link from "next/link";
import { notFound } from "next/navigation";
import { Callback } from "@/components/Callback";
import { LoadFailed } from "@/components/States";
import { getScheme } from "@/lib/api";
import { districtName, needName } from "@/lib/finder";
import { formatDate, isStale } from "@/lib/format";
import { getLang, t } from "@/lib/i18n";

export default async function SchemePage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const lang = await getLang();
  const d = t(lang);
  const s = await getScheme(code);
  if (s === null) notFound();
  if (s === "error") return <div className="wrap page"><LoadFailed text={d.loadError} /></div>;
  // Prefer Hindi in Hindi mode; anything still untranslated is marked so screen readers switch voice.
  const pick = (hi: string, en: string) =>
    lang === "hi" && hi ? { text: hi, lang: "hi" } : { text: en, lang: "en" };
  const who = pick(s.who_can_apply_hi, s.who_can_apply_en);
  const how = pick(s.how_to_apply_hi, s.how_to_apply_en);
  const centre = pick(s.help_centre_hi, s.help_centre);
  const docs = lang === "hi" && s.documents_hi.length > 0 ? s.documents_hi : s.documents;
  return (
    <article className="wrap page">
      <p style={{ marginBottom: "1rem" }}><Link href="/schemes">{d.back}</Link></p>
      <p className="muted">{needName(s.need, lang)}</p>
      <h1>{lang === "hi" ? s.title_hi : s.title_en}</h1>
      <p className="amount-big" style={{ marginTop: "1rem" }}>{(lang === "hi" && s.benefit_hi) || s.benefit_en}</p>
      {s.districts.length > 0 && <p className="muted">{d.district}: {s.districts.map((x) => districtName(x, lang)).join(", ")}</p>}
      <div className="detail" style={{ marginTop: "2rem" }}>
        <div className="stack-l">
          {isStale(s.last_checked) && <p className="notice warn">{d.stale}</p>}
          {lang === "hi" && s.summary_hi && (
            <div className="notice">
              <h2 style={{ fontSize: "1.3rem", marginBottom: "0.25rem" }}>{d.simpleSummary}</h2>
              <p lang="hi">{s.summary_hi}</p>
              <small className="muted">{d.simpleSummaryNote}</small>
            </div>
          )}
          <section><h2>{d.whoCanApply}</h2><p lang={who.lang}>{who.text}</p></section>
          {docs.length > 0 && (
            <section><h2>{d.documents}</h2><ul className="ticks">{docs.map((x) => <li key={x}>{x}</li>)}</ul></section>
          )}
          {how.text && <section><h2>{d.howToApply}</h2><p lang={how.lang}>{how.text}</p></section>}
          {centre.text && <section><h2>{d.helpCentre}</h2><p lang={centre.lang}>{centre.text}</p></section>}
          {s.notice_text && (
            <details className="more"><summary>{d.noticeText}</summary><p lang="en" style={{ whiteSpace: "pre-line" }}>{s.notice_text}</p></details>
          )}
          <p className="muted">
            <a href={s.source_url} rel="noopener noreferrer">{d.source}</a><br />
            {d.lastChecked}: {formatDate(s.last_checked, lang)}
          </p>
        </div>
        <aside className="panel stack">
          <Link className="btn primary" style={{ width: "100%" }} href="/finder">{d.checkFit}</Link>
          <Callback d={d} lang={lang} schemeCode={s.code} open />
        </aside>
      </div>
    </article>
  );
}
