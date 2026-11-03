import type { Metadata } from "next";
import Link from "next/link";
import { DonateForm } from "@/components/DonateForm";
import { DonateSteps } from "@/components/DonateSteps";
import { Empty, LoadFailed } from "@/components/States";
import { getCampaigns, getMe, rupees } from "@/lib/api";
import { getLang, t } from "@/lib/i18n";

export const metadata: Metadata = { title: "Donate" };

export default async function Donate({ searchParams }: { searchParams: Promise<{ campaign?: string }> }) {
  const lang = await getLang();
  const d = t(lang);
  const [campaigns, me] = await Promise.all([getCampaigns(), getMe()]);
  const { campaign } = await searchParams;
  return (
    <section className="wrap page stack" style={{ maxWidth: "46rem" }}>
      <h1>{d.donateTitle}</h1>
      <p className="muted">{d.donateIntro}</p>
      {campaigns === null ? <LoadFailed text={d.loadError} /> : campaigns.length === 0 ? <Empty text={d.noCampaigns} /> : me ? (
        <>
          <DonateSteps d={d} current={1} />
          <DonateForm d={d} lang={lang} campaigns={campaigns} panMasked={me.pan_masked} initialCampaign={campaign} />
        </>
      ) : (
        <>
          <div className="stack">
            {campaigns.map((c) => (
              <article key={c.slug} className="panel campaign">
                <h2 style={{ fontSize: "1.3rem" }}>{lang === "hi" ? c.title_hi : c.title_en}</h2>
                <p className="muted">{(lang === "hi" && c.description_hi) || c.description_en}</p>
                <p><strong>{rupees(c.raised_paise)}</strong> {d.raised}{c.goal_paise ? `, ${d.goal} ${rupees(c.goal_paise)}` : ""}</p>
                {c.goal_paise ? <progress max={c.goal_paise} value={Math.min(c.raised_paise, c.goal_paise)} aria-label={d.raised} /> : null}
              </article>
            ))}
          </div>
          <div className="notice stack">
            <p>{d.signInToDonate}</p>
            <div className="row">
              <Link href="/login?next=/donate" className="btn primary">{d.login}</Link>
              <Link href="/register?next=/donate" className="btn">{d.register}</Link>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
