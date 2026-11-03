import Link from "next/link";
import { getSchemes } from "@/lib/api";
import { getLang, t } from "@/lib/i18n";

export default async function Schemes() {
  const lang = await getLang();
  const d = t(lang);
  const schemes = await getSchemes();
  return (
    <section>
      <h1>{d.schemes}</h1>
      {schemes === null ? (
        <p role="alert">{d.loadError}</p>
      ) : schemes.length === 0 ? (
        <p>{d.noSchemes}</p>
      ) : (
        <div className="grid">
          {schemes.map((s) => (
            <article key={s.code} className="card">
              <h2 style={{ marginTop: 0 }}>
                <Link href={`/schemes/${s.code}`}>{lang === "hi" ? s.title_hi : s.title_en}</Link>
              </h2>
              <p className="muted">{(lang === "hi" && s.benefit_hi) || s.benefit_en}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
