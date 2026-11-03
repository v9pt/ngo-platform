import Link from "next/link";
import { redirect } from "next/navigation";
import { type AdminScheme, authedFetch, getMe } from "@/lib/api";
import { transition } from "./actions";

const NEXT: Record<string, { to: string; label: string; roles: string[] }[]> = {
  draft: [{ to: "in_review", label: "Submit for review", roles: ["editor", "admin"] }],
  in_review: [
    { to: "published", label: "Publish", roles: ["admin"] },
    { to: "draft", label: "Send back to draft", roles: ["admin"] },
  ],
  published: [{ to: "draft", label: "Unpublish to draft", roles: ["admin"] }],
};

export default async function Admin() {
  const me = await getMe();
  if (!me) redirect("/login");
  if (me.role === "donor") redirect("/account");
  const r = await authedFetch("/v1/admin/schemes");
  if (!r.ok) return <p role="alert">Could not load schemes.</p>;
  const schemes = (await r.json()) as AdminScheme[];
  return (
    <section lang="en">
      <h1>Scheme editor</h1>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <caption className="muted" style={{ textAlign: "left" }}>Schemes and their publishing status</caption>
          <thead><tr><th scope="col" align="left">Scheme</th><th scope="col" align="left">Status</th><th scope="col" align="left">Actions</th></tr></thead>
          <tbody>
            {schemes.map((s) => (
              <tr key={s.code} style={{ borderTop: "1px solid var(--border)" }}>
                <td><Link href={`/admin/schemes/${s.code}`}>{s.code} · {s.title_en}</Link></td>
                <td>{s.status.replace("_", " ")}</td>
                <td style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", paddingBlock: "0.4rem" }}>
                  {(NEXT[s.status] ?? []).filter((n) => n.roles.includes(me.role)).map((n) => (
                    <form key={n.to} action={transition}>
                      <input type="hidden" name="code" value={s.code} />
                      <input type="hidden" name="to" value={n.to} />
                      <button type="submit">{n.label}</button>
                    </form>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
