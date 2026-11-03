import type { Metadata } from "next";
import Link from "next/link";
import { ActionForm } from "@/components/ActionForm";
import { Empty, LoadFailed } from "@/components/States";
import { StaffNav } from "@/components/StaffNav";
import { type AdminScheme, authedFetch, type Callback } from "@/lib/api";
import { NEEDS } from "@/lib/finder";
import { requireStaff, STATUS_LABEL, TRANSITIONS } from "@/lib/staff";
import { createScheme, transition } from "./actions";

export const metadata: Metadata = { title: "Schemes" };

export default async function Admin() {
  const me = await requireStaff("/admin");
  const [sr, cr] = await Promise.all([authedFetch("/v1/admin/schemes"), authedFetch("/v1/admin/callbacks")]);
  const schemes = sr.ok ? ((await sr.json()) as AdminScheme[]) : null;
  const callbacks = cr.ok ? ((await cr.json()) as Callback[]) : [];
  const count = (status: string) => (schemes ?? []).filter((s) => s.status === status).length;
  return (
    <section className="wrap page stack-l" lang="en">
      <div>
        <h1>Trust office</h1>
        <p className="muted">Signed in as {me.full_name}, {me.role}.</p>
      </div>
      <StaffNav role={me.role} current="schemes" />
      {schemes === null ? <LoadFailed text="The schemes could not load. Try again shortly." /> : (
        <>
          <div className="stats">
            <div><strong>{count("in_review")}</strong> waiting for review</div>
            <div><strong>{count("draft")}</strong> drafts</div>
            <div><strong>{count("published")}</strong> published</div>
            <div><strong>{callbacks.filter((c) => c.status === "new").length}</strong> call-backs to make</div>
          </div>
          {schemes.length === 0 ? <Empty text="No schemes yet. Add the first one below." /> : (
            <table className="data stack">
              <caption>Schemes and where each one is in review</caption>
              <thead><tr><th scope="col">Scheme</th><th scope="col">Status</th><th scope="col">Next step</th></tr></thead>
              <tbody>
                {schemes.map((s) => (
                  <tr key={s.code}>
                    <td><Link href={`/admin/schemes/${s.code}`}>{s.title_en}</Link><br /><small className="muted">{s.code}</small></td>
                    <td><span className={`tag ${s.status}`}>{STATUS_LABEL[s.status] ?? s.status}</span></td>
                    <td>
                      <div className="row">
                        {(TRANSITIONS[s.status] ?? []).filter((n) => n.roles.includes(me.role)).map((n) => (
                          <ActionForm key={n.to} action={transition} className="stack">
                            <input type="hidden" name="code" value={s.code} />
                            <input type="hidden" name="to" value={n.to} />
                            <button type="submit">{n.label}</button>
                          </ActionForm>
                        ))}
                        {(TRANSITIONS[s.status] ?? []).every((n) => !n.roles.includes(me.role)) && <span className="muted">Waiting for an admin</span>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <section className="panel stack">
            <h2>Add a scheme</h2>
            <p className="muted">It starts as a private draft. You fill in the details and rules on the next screen.</p>
            <ActionForm action={createScheme} className="form-grid two">
              <div className="field"><label htmlFor="title_en">Title in English</label><input id="title_en" name="title_en" required maxLength={200} /></div>
              <div className="field"><label htmlFor="title_hi">Title in Hindi</label><input id="title_hi" name="title_hi" lang="hi" required maxLength={300} /></div>
              <div className="field"><label htmlFor="need">Need</label>
                <select id="need" name="need">{NEEDS.map((n) => <option key={n.value} value={n.value}>{n.en}</option>)}</select></div>
              <div className="field" style={{ alignSelf: "end" }}><button type="submit" className="primary">Create draft</button></div>
            </ActionForm>
          </section>
        </>
      )}
    </section>
  );
}
