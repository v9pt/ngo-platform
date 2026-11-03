import type { Metadata } from "next";
import { Finder } from "@/components/Finder";
import { getLang, t } from "@/lib/i18n";

export const metadata: Metadata = { title: "Find your scheme" };

export default async function FinderPage() {
  const lang = await getLang();
  const d = t(lang);
  return (
    <section className="wrap page stack" style={{ maxWidth: "52rem" }}>
      <h1>{d.finder}</h1>
      <p className="muted">{d.heroText}</p>
      <Finder d={d} lang={lang} />
    </section>
  );
}
