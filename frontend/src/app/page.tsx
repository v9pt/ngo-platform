import Link from "next/link";
import { getLang, t } from "@/lib/i18n";

export default async function Home() {
  const d = t(await getLang());
  return (
    <section>
      <h1>{d.heroTitle}</h1>
      <p className="muted">{d.heroText}</p>
      <p style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <Link href="/finder" className="btn primary">{d.startFinder}</Link>
        <Link href="/schemes" className="btn">{d.browseSchemes}</Link>
      </p>
    </section>
  );
}
