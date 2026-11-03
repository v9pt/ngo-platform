import Link from "next/link";
import { notFound } from "next/navigation";
import { ActionForm } from "@/components/ActionForm";
import { RulesEditor } from "@/components/RulesEditor";
import { LoadFailed } from "@/components/States";
import { type AdminSchemeDetail, type AdminSummary, type AuditEntry, authedFetch } from "@/lib/api";
import { DISTRICTS, NEEDS } from "@/lib/finder";
import { formatDate } from "@/lib/format";
import { requireStaff, STATUS_LABEL, TRANSITIONS } from "@/lib/staff";
import { draftSummary, editSummary, reviewSummary, saveScheme, transition, writeSummary } from "../../actions";

const ACTION: Record<string, string> = {
  "scheme.create": "created this scheme", "scheme.edit": "edited it", "scheme.transition": "changed its status",
  "summary.draft": "asked AI for a draft", "summary.write": "wrote a summary", "summary.edit": "edited a summary",
  "summary.approve": "approved a summary", "summary.reject": "rejected a summary",
};

export default async function EditScheme({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const me = await requireStaff(`/admin/schemes/${code}`);
  const enc = encodeURIComponent(code);
  const [sr, ur, hr] = await Promise.all([
    authedFetch(`/v1/admin/schemes/${enc}`),
    authedFetch(`/v1/admin/schemes/${enc}/summaries`),
    authedFetch(`/v1/admin/schemes/${enc}/history`),
  ]);
  if (sr.status === 404) notFound();
  if (!sr.ok || !ur.ok) return <div className="wrap page"><LoadFailed text="This scheme could not load. Try again shortly." /></div>;
  const s = (await sr.json()) as AdminSchemeDetail;
  const summaries = (await ur.json()) as AdminSummary[];
  const history = hr.ok ? ((await hr.json()) as AuditEntry[]) : [];
  const locked = s.status === "published";
  const text = (name: keyof AdminSchemeDetail, label: string, opts: { rows?: number; hi?: boolean } = {}) => (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      {opts.rows
        ? <textarea id={name} name={name} rows={opts.rows} lang={opts.hi ? "hi" : undefined} defaultValue={String(s[name] ?? "")} />
        : <input id={name} name={name} lang={opts.hi ? "hi" : undefined} defaultValue={String(s[name] ?? "")} />}
    </div>
  );
  return (
    <section className="wrap page stack-l" lang="en">
      <div className="stack">
        <p><Link href="/admin">All schemes</Link></p>
        <h1>{s.title_en}</h1>
        <div className="row">
          <span className={`tag ${s.status}`}>{STATUS_LABEL[s.status] ?? s.status}</span>
          <span className="muted">{s.code}</span>
          {s.status === "published" && <Link href={`/schemes/${s.code}`}>See the public page</Link>}
        </div>
        <div className="row">
          {(TRANSITIONS[s.status] ?? []).filter((n) => n.roles.includes(me.role)).map((n) => (
            <ActionForm key={n.to} action={transition} className="stack">
              <input type="hidden" name="code" value={s.code} />
              <input type="hidden" name="to" value={n.to} />
              <button type="submit" className={n.to === "published" ? "primary" : undefined}>{n.label}</button>
            </ActionForm>
          ))}
        </div>
        {locked && <p className="notice">Published schemes cannot change in place, so what women see always matches what was reviewed. {me.role === "admin" ? "Unpublish it to edit." : "Ask an admin to unpublish it."}</p>}
      </div>

      <ActionForm action={saveScheme} className="stack-l" success="Saved.">
        <input type="hidden" name="code" value={s.code} />
        <fieldset disabled={locked} className="stack-l">
          <section className="stack">
            <h2>Details</h2>
            <div className="form-grid two">
              {text("title_en", "Title in English")}{text("title_hi", "Title in Hindi", { hi: true })}
              {text("benefit_en", "Benefit in English")}{text("benefit_hi", "Benefit in Hindi", { hi: true })}
              {text("who_can_apply_en", "Who can apply, in English", { rows: 2 })}{text("who_can_apply_hi", "Who can apply, in Hindi", { rows: 2, hi: true })}
              <div className="field"><label htmlFor="documents">Documents in English, one per line</label><textarea id="documents" name="documents" rows={3} defaultValue={s.documents.join("\n")} /></div>
              <div className="field"><label htmlFor="documents_hi">Documents in Hindi, one per line</label><textarea id="documents_hi" name="documents_hi" lang="hi" rows={3} defaultValue={s.documents_hi.join("\n")} /></div>
              {text("how_to_apply_en", "How to apply, in English", { rows: 2 })}{text("how_to_apply_hi", "How to apply, in Hindi", { rows: 2, hi: true })}
              {text("help_centre", "Help centre in English")}{text("help_centre_hi", "Help centre in Hindi", { hi: true })}
              <div className="field"><label htmlFor="need">Need</label>
                <select id="need" name="need" defaultValue={s.need}>{NEEDS.map((n) => <option key={n.value} value={n.value}>{n.en}</option>)}</select></div>
              {text("source_url", "Official source link")}
              <div className="field"><label htmlFor="last_checked">Last checked against the source</label><input id="last_checked" name="last_checked" type="date" defaultValue={s.last_checked} /></div>
            </div>
            <fieldset className="field">
              <legend>Runs only in these districts (leave all empty for everywhere)</legend>
              <div className="row">
                {DISTRICTS.map((x) => (
                  <label key={x} className="check"><input type="checkbox" name="districts" value={x} defaultChecked={s.districts.includes(x)} /> {x}</label>
                ))}
              </div>
            </fieldset>
          </section>
          <section className="stack">
            <h2>Eligibility rules</h2>
            <p className="muted measure">A woman must meet all of these. Each one appears in her results in plain words.</p>
            <RulesEditor initial={s.rules} disabled={locked} />
          </section>
          <section className="stack">
            <h2>Official notice</h2>
            <p className="muted measure">The source for AI summaries. Every number in a summary must appear here.</p>
            {text("notice_text", "Notice text", { rows: 6 })}
          </section>
        </fieldset>
        {!locked && <button type="submit" className="primary">Save changes</button>}
      </ActionForm>

      <section className="stack">
        <h2>Hindi summaries</h2>
        <p className="muted measure">AI drafts stay private until an editor approves them. Each is checked for Hindi script, length, and numbers that are not in the notice. A flagged summary cannot be approved.</p>
        <ActionForm action={draftSummary} className="stack">
          <input type="hidden" name="code" value={s.code} />
          <button type="submit" className="primary">Draft with AI</button>
        </ActionForm>
        <details className="more">
          <summary>Write a summary by hand</summary>
          <ActionForm action={writeSummary} className="stack">
            <input type="hidden" name="code" value={s.code} />
            <div className="field"><label htmlFor="new-summary">Summary in Hindi</label><textarea id="new-summary" name="hindi_text" rows={4} lang="hi" required maxLength={2000} /></div>
            <button type="submit">Save as draft</button>
          </ActionForm>
        </details>
        {summaries.length === 0 && <p className="muted">No summaries yet.</p>}
        {summaries.map((u) => (
          <article key={u.id} className="panel stack">
            <div className="row">
              <strong>{u.source === "ai" ? "AI draft" : "Written by hand"}</strong>
              <span className={`tag ${u.status === "approved" ? "published" : u.status === "rejected" ? "closed" : "draft"}`}>{u.status[0].toUpperCase() + u.status.slice(1)}</span>
              {u.checks.needs_attention && <span className="tag failed">Needs attention</span>}
            </div>
            {u.status === "draft" && u.checks.needs_attention && (
              <div className="notice warn">
                <ul style={{ margin: 0, paddingInlineStart: "1.2rem" }}>
                  {u.checks.unmatched_numbers && u.checks.unmatched_numbers.length > 0 && <li>Numbers not in the notice: {u.checks.unmatched_numbers.join(", ")}. Fix or remove them.</li>}
                  {u.checks.devanagari_ok === false && <li>This is not mostly in Hindi script.</li>}
                  {u.checks.length_ok === false && <li>Keep it between 40 and 600 characters.</li>}
                </ul>
              </div>
            )}
            {u.status === "draft" ? (
              <>
                <ActionForm action={editSummary} className="stack" success="Saved and checked again.">
                  <input type="hidden" name="id" value={u.id} />
                  <input type="hidden" name="code" value={s.code} />
                  <div className="field"><label htmlFor={`t-${u.id}`}>Summary in Hindi</label>
                    <textarea id={`t-${u.id}`} name="hindi_text" rows={4} lang="hi" defaultValue={u.hindi_text} /></div>
                  <button type="submit">Save and check again</button>
                </ActionForm>
                <div className="row">
                  <ActionForm action={reviewSummary} className="stack">
                    <input type="hidden" name="id" value={u.id} /><input type="hidden" name="code" value={s.code} /><input type="hidden" name="verb" value="approve" />
                    <button type="submit" className="primary" disabled={u.checks.needs_attention}>Approve</button>
                  </ActionForm>
                  <ActionForm action={reviewSummary} className="stack">
                    <input type="hidden" name="id" value={u.id} /><input type="hidden" name="code" value={s.code} /><input type="hidden" name="verb" value="reject" />
                    <button type="submit">Reject</button>
                  </ActionForm>
                </div>
              </>
            ) : <p lang="hi">{u.hindi_text}</p>}
          </article>
        ))}
      </section>

      <section className="stack">
        <h2>History</h2>
        {history.length === 0 ? <p className="muted">Nothing recorded yet.</p> : (
          <ul className="ticks">
            {history.map((h, i) => (
              <li key={i}><span>{formatDate(h.created_at, "en")}: {h.actor_name ?? "Someone"} {ACTION[h.action] ?? h.action}
                {h.action === "scheme.transition" ? ` from ${String(h.detail.from).replace("_", " ")} to ${String(h.detail.to).replace("_", " ")}` : ""}</span></li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
