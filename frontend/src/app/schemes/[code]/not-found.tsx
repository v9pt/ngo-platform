import { Empty } from "@/components/States";
import { getLang, t } from "@/lib/i18n";

export default async function NotFound() {
  const d = t(await getLang());
  return <div className="wrap page"><Empty text={d.schemeMissing} href="/schemes" action={d.seeAll} /></div>;
}
