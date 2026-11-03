import Link from "next/link";
import { AuthForm } from "@/components/AuthForm";
import { getLang, t } from "@/lib/i18n";

export default async function Login() {
  const d = t(await getLang());
  return (
    <section>
      <h1>{d.login}</h1>
      <AuthForm d={d} mode="login" />
      <p className="muted">{d.haveNoAccount} <Link href="/register">{d.register}</Link></p>
    </section>
  );
}
