import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AuthForm } from "@/components/AuthForm";
import { getMe } from "@/lib/api";
import { safeNext } from "@/lib/format";
import { getLang, t } from "@/lib/i18n";

export const metadata: Metadata = { title: "Login" };

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const d = t(await getLang());
  const next = safeNext((await searchParams).next) ?? undefined;
  const me = await getMe();
  if (me) redirect(next ?? (me.role === "donor" ? "/account" : "/admin"));
  return (
    <section className="wrap page stack">
      <h1>{d.loginTitle}</h1>
      <p className="muted measure">{d.whyAccount}</p>
      <AuthForm d={d} mode="login" next={next} showDemo={process.env.SHOW_DEMO_LOGINS !== "false"} />
    </section>
  );
}
