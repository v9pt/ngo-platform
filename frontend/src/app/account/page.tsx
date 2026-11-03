import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { CancelMandate } from "@/components/CancelMandate";
import { LogoutButton } from "@/components/LogoutButton";
import { PanForm } from "@/components/PanForm";
import { Empty, LoadFailed } from "@/components/States";
import { authedFetch, type Donation, getMe, type Mandate, rupees } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { getLang, t } from "@/lib/i18n";

export const metadata: Metadata = { title: "My account" };

export default async function Account() {
  const lang = await getLang();
  const d = t(lang);
  const me = await getMe();
  if (!me) redirect("/login?next=/account");
  const [dr, mr] = await Promise.all([authedFetch("/v1/donations"), authedFetch("/v1/mandates")]);
  const donations = dr.ok ? ((await dr.json()) as Donation[]) : null;
  const mandates = mr.ok ? ((await mr.json()) as Mandate[]) : [];
  return (
    <section className="wrap page stack-l">
      <div className="result-head">
        <div>
          <h1>{d.account}</h1>
          <p>{me.full_name}</p>
          <p className="muted" style={{ overflowWrap: "anywhere" }}>{me.email}</p>
        </div>
        <LogoutButton label={d.logout} />
      </div>

      <section className="panel stack">
        <h2>{d.panTitle}</h2>
        <PanForm d={d} masked={me.pan_masked} />
      </section>

      {mandates.length > 0 && (
        <section className="stack">
          <h2>{d.mandates}</h2>
          {mandates.map((m) => (
            <div key={m.id} className="panel stack">
              <div className="result-head">
                <strong>{rupees(m.amount_paise)} {d.giftFor} {lang === "hi" ? m.campaign_title_hi : m.campaign_title_en}</strong>
                <span className={`tag ${m.status === "active" ? "paid" : "cancelled"}`}>{m.status === "active" ? d.mandateActive : d.mandateCancelled}</span>
              </div>
              {m.status === "active" && (
                <>
                  <p className="muted">{d.nextCharge}: {formatDate(m.next_charge_on, lang)}</p>
                  <CancelMandate d={d} id={m.id} />
                </>
              )}
            </div>
          ))}
        </section>
      )}

      <section className="stack">
        <h2>{d.history}</h2>
        {donations === null ? <LoadFailed text={d.loadError} /> : donations.length === 0 ? (
          <Empty text={d.noDonations} href="/donate" action={d.firstGift} />
        ) : (
          <table className="data stack">
            <thead>
              <tr>
                <th scope="col">{d.campaign}</th><th scope="col">{d.date}</th>
                <th scope="col" className="num">{d.amount}</th><th scope="col">{d.status}</th><th scope="col">{d.receipt}</th>
              </tr>
            </thead>
            <tbody>
              {donations.map((x) => (
                <tr key={x.id}>
                  <td><strong>{lang === "hi" ? x.campaign_title_hi : x.campaign_title_en}</strong></td>
                  <td data-label={d.date}>{x.created_at ? formatDate(x.created_at, lang) : ""}</td>
                  <td data-label={d.amount} className="num">{rupees(x.amount_paise)}</td>
                  <td><span className={`tag ${x.status}`}>{d[`status_${x.status}` as "status_paid"]}</span></td>
                  <td>
                    {x.receipt_number ? (
                      <>
                        <a href={`/api/v1/donations/${x.id}/receipt.pdf`}>{x.receipt_number}</a><br />
                        <small className="muted">{x.has_80g ? d.certShort : d.plainShort}</small>
                      </>
                    ) : (
                      <Link href={`/donate/pay/${x.id}`}>{x.status === "failed" ? d.tryAgainPay : d.completePayment}</Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </section>
  );
}
