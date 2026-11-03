import { Finder } from "@/components/Finder";
import { getLang, t } from "@/lib/i18n";

export default async function FinderPage() {
  const lang = await getLang();
  const d = t(lang);
  return (
    <section>
      <h1>{d.finder}</h1>
      <p className="muted">{d.heroText}</p>
      <Finder d={d} lang={lang} />
    </section>
  );
}
