import Link from "next/link";
import { DonateForm } from "@/components/DonateForm";
import { getCampaigns, getMe, rupees } from "@/lib/api";
import { getLang, t } from "@/lib/i18n";

export default async function Donate() {
  const lang = await getLang();
  const d = t(lang);
  const [campaigns, me] = await Promise.all([getCampaigns(), getMe()]);
  if (campaigns === null) return <p role="alert">{d.loadError}</p>;
  return (
    <section>
      <h1>{d.donate}</h1>
      <div className="grid" style={{ marginBottom: "1.5rem" }}>
        {campaigns.map((c) => (
          <article key={c.slug} className="card">
            <h2 style={{ marginTop: 0 }}>{lang === "hi" ? c.title_hi : c.title_en}</h2>
            <p className="muted">{(lang === "hi" && c.description_hi) || c.description_en}</p>
            <p>
              {d.raised}: <strong>{rupees(c.raised_paise)}</strong>
              {c.goal_paise ? <> · {d.goal}: {rupees(c.goal_paise)}</> : null}
            </p>
            {c.goal_paise ? (
              <progress max={c.goal_paise} value={Math.min(c.raised_paise, c.goal_paise)} style={{ width: "100%" }}
                        aria-label={d.raised} />
            ) : null}
          </article>
        ))}
      </div>
      {me ? (
        campaigns.length > 0 ? <DonateForm d={d} lang={lang} campaigns={campaigns} /> : <p>{d.noSchemes}</p>
      ) : (
        <p>
          {d.signInToDonate}{" "}
          <Link href="/login" className="btn primary">{d.login}</Link>{" "}
          <Link href="/register" className="btn">{d.register}</Link>
        </p>
      )}
    </section>
  );
}
