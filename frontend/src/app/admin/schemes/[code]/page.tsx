import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { type AdminScheme, type AdminSummary, authedFetch, getMe } from "@/lib/api";
import { draftSummary, editSummary, reviewSummary, saveNotice } from "../../actions";

export default async function EditScheme({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const me = await getMe();
  if (!me) redirect("/login");
  if (me.role === "donor") redirect("/account");
  const [all, sums] = await Promise.all([
    authedFetch("/v1/admin/schemes"),
    authedFetch(`/v1/admin/schemes/${encodeURIComponent(code)}/summaries`),
  ]);
  if (!all.ok || !sums.ok) return <p role="alert">Could not load this scheme.</p>;
  const scheme = ((await all.json()) as AdminScheme[]).find((s) => s.code === code);
  if (!scheme) notFound();
  const summaries = (await sums.json()) as AdminSummary[];
  const locked = scheme.status === "published";
  return (
    <section lang="en">
      <p><Link href="/admin">← All schemes</Link></p>
      <h1>{scheme.code} · {scheme.title_en}</h1>
      <p className="muted">Status: {scheme.status.replace("_", " ")}{locked ? " (unpublish to edit)" : ""}</p>

      <h2>Official notice (source for AI drafts)</h2>
      <form action={saveNotice}>
        <input type="hidden" name="code" value={code} />
        <div className="field">
          <label htmlFor="notice_text">Notice text</label>
          <textarea id="notice_text" name="notice_text" rows={8} defaultValue={scheme.notice_text} disabled={locked}
                    style={{ width: "100%", font: "inherit", padding: "0.5rem" }} />
        </div>
        <button type="submit" disabled={locked}>Save notice</button>
      </form>

      <h2>Hindi summaries</h2>
      <form action={draftSummary}>
        <input type="hidden" name="code" value={code} />
        <button type="submit" className="primary">Draft Hindi summary with AI</button>
      </form>
      <p className="muted">AI drafts are never shown to the public until an editor approves them.</p>
      {summaries.length === 0 && <p>No summaries yet.</p>}
      {summaries.map((s) => (
        <article key={s.id} className="card" style={{ marginBottom: "1rem" }}>
          <p>
            <strong>{s.source === "ai" ? "AI draft" : "Human"}</strong> · {s.status}
            {s.checks.needs_attention && <span className="badge possible" style={{ marginLeft: "0.5rem" }}>needs attention</span>}
          </p>
          {s.checks.needs_attention && (
            <ul>
              {s.checks.unmatched_numbers && s.checks.unmatched_numbers.length > 0 && (
                <li>Numbers not in the notice: {s.checks.unmatched_numbers.join(", ")}</li>
              )}
              {s.checks.devanagari_ok === false && <li>Not mostly Devanagari script</li>}
              {s.checks.length_ok === false && <li>Length outside 40 to 600 characters</li>}
            </ul>
          )}
          {s.status === "draft" ? (
            <>
              <form action={editSummary}>
                <input type="hidden" name="id" value={s.id} />
                <input type="hidden" name="code" value={code} />
                <label htmlFor={`t-${s.id}`}>Summary (Hindi)</label>
                <textarea id={`t-${s.id}`} name="hindi_text" rows={5} lang="hi" defaultValue={s.hindi_text}
                          style={{ width: "100%", font: "inherit", padding: "0.5rem" }} />
                <button type="submit">Save and re-check</button>
              </form>
              <form action={reviewSummary} style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                <input type="hidden" name="id" value={s.id} />
                <input type="hidden" name="code" value={code} />
                <button type="submit" name="verb" value="approve" className="primary" disabled={s.checks.needs_attention}>Approve</button>
                <button type="submit" name="verb" value="reject">Reject</button>
              </form>
            </>
          ) : (
            <p lang="hi">{s.hindi_text}</p>
          )}
        </article>
      ))}
    </section>
  );
}
