import Link from "next/link";
import { AuthForm } from "@/components/AuthForm";
import { getLang, t } from "@/lib/i18n";

export default async function Register() {
  const d = t(await getLang());
  return (
    <section>
      <h1>{d.register}</h1>
      <AuthForm d={d} mode="register" />
      <p className="muted">{d.haveAccount} <Link href="/login">{d.login}</Link></p>
    </section>
  );
}
