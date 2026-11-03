import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { authedFetch, type Donation, getMe, rupees } from "@/lib/api";
import { getLang, t } from "@/lib/i18n";
import { simulatePayment } from "./actions";

export default async function Pay({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const d = t(await getLang());
  if (!(await getMe())) redirect("/login");
  const r = await authedFetch(`/v1/donations/${encodeURIComponent(id)}`);
  if (r.status === 404 || r.status === 422) notFound();
  if (!r.ok) return <p role="alert">{d.loadError}</p>;
  const donation = (await r.json()) as Donation;

  if (donation.status === "paid") {
    return (
      <section>
        <h1>{d.thanks}</h1>
        <p>{d.receipt}: <strong>{donation.receipt_number}</strong> · {rupees(donation.amount_paise)}</p>
        <p>
          <a className="btn primary" href={`/api/v1/donations/${donation.id}/receipt.pdf`}>{d.downloadReceipt}</a>{" "}
          <Link className="btn" href="/account">{d.account}</Link>
        </p>
      </section>
    );
  }
  return (
    <section>
      <h1>{d.payTitle}</h1>
      <p className="muted">{d.payNote}</p>
      <p>{rupees(donation.amount_paise)} · {d[`status_${donation.status}` as "status_paid"]}</p>
      {donation.status === "pending" && (
        <form action={simulatePayment} style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <input type="hidden" name="gateway_ref" value={donation.gateway_ref} />
          <input type="hidden" name="donation_id" value={donation.id} />
          <button type="submit" name="event" value="payment.succeeded" className="primary">{d.paySuccess}</button>
          <button type="submit" name="event" value="payment.failed">{d.payFail}</button>
        </form>
      )}
    </section>
  );
}
