import type { Metadata } from "next";
import { ActionForm } from "@/components/ActionForm";
import { Empty, LoadFailed } from "@/components/States";
import { StaffNav } from "@/components/StaffNav";
import { authedFetch, type Callback } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { requireStaff } from "@/lib/staff";
import { finishCallback } from "../actions";

export const metadata: Metadata = { title: "Call-backs" };

export default async function Callbacks() {
  const me = await requireStaff("/admin/callbacks");
  const r = await authedFetch("/v1/admin/callbacks");
  const rows = r.ok ? ((await r.json()) as Callback[]) : null;
  return (
    <section className="wrap page stack" lang="en">
      <h1>Call-backs</h1>
      <StaffNav role={me.role} current="callbacks" />
      <p className="muted measure">Women who asked the helpline to call them. Numbers are personal data: use them only to make this call.</p>
      {rows === null ? <LoadFailed text="The list could not load. Try again shortly." /> : rows.length === 0 ? <Empty text="No one has asked for a call yet." /> : (
        <table className="data stack">
          <thead><tr><th scope="col">Person</th><th scope="col">Asked about</th><th scope="col">Asked on</th><th scope="col">Status</th><th scope="col"><span className="visually-hidden">Action</span></th></tr></thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}>
                <td>{c.name && <strong lang="hi">{c.name}<br /></strong>}<a href={`tel:+91${c.phone}`}>{c.phone}</a></td>
                <td data-label="Asked about">{c.scheme_code ?? "General help"}</td>
                <td data-label="Asked on">{formatDate(c.created_at, "en")}</td>
                <td><span className={`tag ${c.status}`}>{c.status === "new" ? "To call" : "Done"}</span></td>
                <td>{c.status === "new" && (
                  <ActionForm action={finishCallback} className="stack">
                    <input type="hidden" name="id" value={c.id} />
                    <button type="submit">Mark as called</button>
                  </ActionForm>
                )}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
