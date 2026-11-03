import Link from "next/link";
import { Callback } from "@/components/Callback";
import { Finder } from "@/components/Finder";
import { LoadFailed } from "@/components/States";
import { getCampaigns, getSchemes, rupees } from "@/lib/api";
import { NEEDS, needName } from "@/lib/finder";
import { fill } from "@/lib/format";
import { getLang, t } from "@/lib/i18n";

export default async function Home() {
  const lang = await getLang();
  const d = t(lang);
  const [schemes, campaigns] = await Promise.all([getSchemes(), getCampaigns()]);
  const campaign = campaigns?.[0];
  const counts = new Map<string, number>();
  for (const s of schemes ?? []) counts.set(s.need, (counts.get(s.need) ?? 0) + 1);
  return (
    <>
      <section className="hero">
        <div className="print-strip" aria-hidden="true" />
        <div className="wrap">
          <h1>{d.heroTitle}</h1>
          <p>{d.heroText}</p>
        </div>
      </section>
      <section className="wrap hero-print" aria-label={d.finder}>
        <Finder d={d} lang={lang} />
      </section>

      <section className="wrap" aria-labelledby="by-need">
        <h2 id="by-need" style={{ marginBottom: "1rem" }}>{d.byNeed}</h2>
        {schemes === null ? <LoadFailed text={d.loadError} /> : (
          <div className="need-list">
            {NEEDS.filter((n) => counts.has(n.value)).map((n) => (
              <Link key={n.value} href={`/schemes?need=${n.value}`}>
                {n[lang]}
                <span className="count">{counts.get(n.value) === 1 ? d.schemeOne : fill(d.schemeCount, { n: counts.get(n.value) ?? 0 })}</span>
              </Link>
            ))}
          </div>
        )}
      </section>

      {schemes && schemes.length > 0 && (
        <section className="wrap section-gap" aria-labelledby="latest">
          <h2 id="latest" style={{ marginBottom: "0.5rem" }}>{d.latestChecked}</h2>
          <div>
            {[...schemes].slice(0, 4).map((s) => (
              <div key={s.code} className="scheme-row">
                <Link href={`/schemes/${s.code}`}>{lang === "hi" ? s.title_hi : s.title_en}</Link>
                <span className="benefit">{(lang === "hi" && s.benefit_hi) || s.benefit_en}</span>
                <span className="muted">{needName(s.need, lang)}</span>
              </div>
            ))}
          </div>
          <p style={{ marginTop: "1rem" }}><Link href="/schemes">{d.seeAll}</Link></p>
        </section>
      )}

      <section className="band section-gap" aria-labelledby="how">
        <div className="wrap two-col">
          <div className="stack">
            <h2 id="how">{d.howTitle}</h2>
            <ol className="stack" style={{ paddingInlineStart: "1.4rem", margin: 0 }}>
              <li>{d.how1}</li><li>{d.how2}</li><li>{d.how3}</li>
            </ol>
          </div>
          <div className="panel"><Callback d={d} lang={lang} open /></div>
        </div>
      </section>

      <section className="wrap section-gap" aria-labelledby="give" style={{ paddingBottom: "4.5rem" }}>
        <div className="two-col">
          <div className="stack">
            <h2 id="give">{d.giveTitle}</h2>
            <p className="measure">{d.giveText}</p>
            <p><Link href="/donate" className="btn primary">{d.donate}</Link></p>
          </div>
          {campaign && (
            <div className="campaign">
              <h3>{lang === "hi" ? campaign.title_hi : campaign.title_en}</h3>
              <p><strong>{rupees(campaign.raised_paise)}</strong> {d.raised}{campaign.goal_paise ? `, ${d.goal} ${rupees(campaign.goal_paise)}` : ""}</p>
              {campaign.goal_paise ? <progress max={campaign.goal_paise} value={Math.min(campaign.raised_paise, campaign.goal_paise)} aria-label={d.raised} /> : null}
            </div>
          )}
        </div>
      </section>
    </>
  );
}
