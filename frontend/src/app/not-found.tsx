import Link from "next/link";
import { getLang, t } from "@/lib/i18n";

export default async function NotFound() {
  const d = t(await getLang());
  return (
    <section className="wrap page stack">
      <h1>{d.notFound}</h1>
      <p><Link className="btn primary" href="/">{d.goHome}</Link></p>
    </section>
  );
}
