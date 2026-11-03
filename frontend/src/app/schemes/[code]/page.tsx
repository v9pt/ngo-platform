import Link from "next/link";
import { notFound } from "next/navigation";
import { getScheme } from "@/lib/api";
import { getLang, t } from "@/lib/i18n";

export default async function SchemePage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const lang = await getLang();
  const d = t(lang);
  const s = await getScheme(code);
  if (s === null) notFound();
  if (s === "error") return <p role="alert">{d.loadError}</p>;
  return (
    <article>
      <p><Link href="/schemes">← {d.back}</Link></p>
      <h1>{lang === "hi" ? s.title_hi : s.title_en}</h1>
      {lang === "hi" && s.summary_hi && <p className="card" lang="hi">{s.summary_hi}</p>}
      <h2>{d.benefit}</h2>
      <p>{(lang === "hi" && s.benefit_hi) || s.benefit_en}</p>
      <h2>{d.whoCanApply}</h2>
      <p>{s.who_can_apply_en}</p>
      {s.documents.length > 0 && (
        <>
          <h2>{d.documents}</h2>
          <ul>{s.documents.map((x) => <li key={x}>{x}</li>)}</ul>
        </>
      )}
      {s.how_to_apply_en && (<><h2>{d.howToApply}</h2><p>{s.how_to_apply_en}</p></>)}
      {s.help_centre && (<><h2>{d.helpCentre}</h2><p>{s.help_centre}</p></>)}
      <p className="muted">
        <a href={s.source_url} rel="noopener noreferrer">{d.source}</a> · {d.lastChecked}: {s.last_checked}
      </p>
    </article>
  );
}
