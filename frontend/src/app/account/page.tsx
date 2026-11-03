import { redirect } from "next/navigation";
import { LogoutButton } from "@/components/LogoutButton";
import { authedFetch, type Donation, getMe, rupees } from "@/lib/api";
import { getLang, t } from "@/lib/i18n";

export default async function Account() {
  const d = t(await getLang());
  const me = await getMe();
  if (!me) redirect("/login");
  const r = await authedFetch("/v1/donations");
  const donations = r.ok ? ((await r.json()) as Donation[]) : null;
  return (
    <section>
      <h1>{d.account}</h1>
      <p>{me.full_name} · <span className="muted">{me.email}</span></p>
      <p><LogoutButton label={d.logout} /></p>
      <h2>{d.history}</h2>
      {donations === null ? (
        <p role="alert">{d.loadError}</p>
      ) : donations.length === 0 ? (
        <p>{d.noDonations}</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th scope="col" align="left">{d.campaign}</th>
                <th scope="col" align="right">{d.amount}</th>
                <th scope="col" align="left">&nbsp;</th>
                <th scope="col" align="left">{d.receipt}</th>
              </tr>
            </thead>
            <tbody>
              {donations.map((x) => (
                <tr key={x.id} style={{ borderTop: "1px solid var(--border)" }}>
                  <td>{x.campaign_slug}</td>
                  <td align="right">{rupees(x.amount_paise)}</td>
                  <td>{d[`status_${x.status}` as "status_paid"]}</td>
                  <td>
                    {x.receipt_number ? (
                      <a href={`/api/v1/donations/${x.id}/receipt.pdf`}>{x.receipt_number}</a>
                    ) : x.status === "pending" ? (
                      <a href={`/donate/pay/${x.id}`}>{d.payTitle}</a>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
