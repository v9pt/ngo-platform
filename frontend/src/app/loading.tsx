import { PageSkeleton } from "@/components/States";
import { getLang } from "@/lib/i18n";

export default async function Loading() {
  return <PageSkeleton label={(await getLang()) === "hi" ? "लोड हो रहा है" : "Loading"} />;
}
