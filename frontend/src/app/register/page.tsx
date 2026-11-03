import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AuthForm } from "@/components/AuthForm";
import { getMe } from "@/lib/api";
import { safeNext } from "@/lib/format";
import { getLang, t } from "@/lib/i18n";

export const metadata: Metadata = { title: "Register" };

export default async function RegisterPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const d = t(await getLang());
  const next = safeNext((await searchParams).next) ?? undefined;
  const me = await getMe();
  if (me) redirect(next ?? (me.role === "donor" ? "/account" : "/admin"));
  return (
    <section className="wrap page stack">
      <h1>{d.registerTitle}</h1>
      <p className="muted measure">{d.whyAccount}</p>
      <AuthForm d={d} mode="register" next={next} showDemo={process.env.SHOW_DEMO_LOGINS !== "false"} />
    </section>
  );
}
