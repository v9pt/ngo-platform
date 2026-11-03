import type { Metadata } from "next";
import { RunMonthly } from "@/components/RunMonthly";
import { Empty, LoadFailed } from "@/components/States";
import { StaffNav } from "@/components/StaffNav";
import { authedFetch, type CampaignReport, rupees } from "@/lib/api";
import { requireStaff } from "@/lib/staff";

export const metadata: Metadata = { title: "Campaign reports" };

export default async function Reports() {
  const me = await requireStaff("/admin/reports", ["admin"]);
  const r = await authedFetch("/v1/admin/campaigns");
  const rows = r.ok ? ((await r.json()) as CampaignReport[]) : null;
  return (
    <section className="wrap page stack-l" lang="en">
      <div className="stack">
        <h1>Campaign reports</h1>
        <StaffNav role={me.role} current="reports" />
      </div>
      {rows === null ? <LoadFailed text="The report could not load. Try again shortly." /> : rows.length === 0 ? <Empty text="No campaigns yet." /> : (
        <div className="stack">
          <table className="data stack">
            <caption>Money counts paid donations only. The export lists every receipt, with PAN masked.</caption>
            <thead><tr><th scope="col">Campaign</th><th scope="col" className="num">Raised</th><th scope="col" className="num">Goal</th><th scope="col" className="num">Paid</th><th scope="col" className="num">Pending</th><th scope="col" className="num">Failed</th><th scope="col">10BD-style export</th></tr></thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.slug}>
                  <td><strong>{c.title_en}</strong><br /><span className={`tag ${c.status === "live" ? "published" : "draft"}`}>{c.status}</span></td>
                  <td data-label="Raised" className="num">{rupees(c.paid_paise)}</td>
                  <td data-label="Goal" className="num">{c.goal_paise ? rupees(c.goal_paise) : "None"}</td>
                  <td data-label="Paid" className="num">{c.paid_count}</td>
                  <td data-label="Pending" className="num">{c.pending_count}</td>
                  <td data-label="Failed" className="num">{c.failed_count}</td>
                  <td><a href={`/api/v1/admin/campaigns/${c.slug}/donations.csv`}>Download CSV</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <section className="panel stack">
        <h2>Monthly giving</h2>
        <p className="muted measure">Test mode: this stands in for a nightly job. It charges every mandate that is due and issues receipts. Running it twice in a day charges nobody twice.</p>
        <RunMonthly />
      </section>
    </section>
  );
}
