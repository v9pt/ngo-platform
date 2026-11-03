import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { DonateSteps } from "@/components/DonateSteps";
import { PanForm } from "@/components/PanForm";
import { PayForm } from "@/components/PayForm";
import { LoadFailed } from "@/components/States";
import { authedFetch, type Donation, getMe, rupees } from "@/lib/api";
import { fill } from "@/lib/format";
import { type Dict, getLang, t } from "@/lib/i18n";

export const metadata: Metadata = { title: "Payment" };

const reasonText = (d: Dict, reason: string | null) =>
  ({ declined: d.reason_declined, insufficient_funds: d.reason_insufficient_funds, foreign_card: d.reason_foreign_card })[reason ?? ""] ?? d.reason_unknown;

export default async function Pay({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const lang = await getLang();
  const d = t(lang);
  const me = await getMe();
  if (!me) redirect(`/login?next=${encodeURIComponent(`/donate/pay/${id}`)}`);
  const r = await authedFetch(`/v1/donations/${encodeURIComponent(id)}`);
  if (r.status === 404 || r.status === 422) notFound();
  if (!r.ok) return <div className="wrap page"><LoadFailed text={d.loadError} /></div>;
  const donation = (await r.json()) as Donation;
  const title = lang === "hi" ? donation.campaign_title_hi : donation.campaign_title_en;

  if (donation.status === "paid") {
    return (
      <section className="wrap page stack" style={{ maxWidth: "46rem" }}>
        <DonateSteps d={d} current={3} />
        <h1>{d.thanks}</h1>
        <p>{rupees(donation.amount_paise)} {d.giftFor} {title}</p>
        <div className="panel stack">
          <p className="muted">{d.receipt}</p>
          <p className="receipt-no">{donation.receipt_number}</p>
          <p className={donation.has_80g ? "notice ok" : "notice warn"}>{donation.has_80g ? d.certIssued : d.plainIssued}</p>
          {donation.kind === "monthly" && <p className="notice">{d.monthlyStarted}</p>}
          <div className="row">
            <a className="btn primary" href={`/api/v1/donations/${donation.id}/receipt.pdf`}>{d.downloadReceipt}</a>
            <Link className="btn" href="/account">{d.account}</Link>
            <Link className="btn" href="/donate">{d.giveAgain}</Link>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="wrap page stack" style={{ maxWidth: "46rem" }}>
      <DonateSteps d={d} current={2} />
      <h1>{d.payTitle}</h1>
      <p className="amount-big">{rupees(donation.amount_paise)}</p>
      <p>{title}</p>
      <p className="notice warn">{d.testBanner}</p>
      {donation.status === "failed" && <p className="notice error" role="alert">{reasonText(d, donation.failure_reason)}</p>}
      {!me.pan_masked && (
        <details className="more"><summary>{d.panAddCta}</summary><PanForm d={d} masked={null} /></details>
      )}
      <PayForm d={d} lang={lang} donationId={donation.id} label={fill(d.payNow, { amount: rupees(donation.amount_paise) })} />
    </section>
  );
}
