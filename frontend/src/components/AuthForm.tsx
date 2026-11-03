"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { safeNext } from "@/lib/format";
import type { Dict } from "@/lib/i18n";

const DEMO_PASSWORD = "DemoPass#2026"; // public demo credential, documented in deployment.md

export function AuthForm({ d, mode, next, showDemo }: { d: Dict; mode: "login" | "register"; next?: string; showDemo: boolean }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const qs = next ? `?next=${encodeURIComponent(next)}` : "";

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const body: Record<string, string> = { email, password };
    if (mode === "register") body.full_name = name;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`/api/v1/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (r.status === 401) return setError(d.authError);
      if (r.status === 409) return setError(d.authTaken);
      if (r.status === 422) return setError(d.authInvalid);
      if (r.status === 429) return setError(d.authLimit);
      if (!r.ok) throw new Error(String(r.status));
      const me = (await r.json()) as { role: string };
      router.push(safeNext(next) ?? (me.role === "donor" ? "/account" : "/admin"));
      router.refresh();
    } catch {
      setError(d.netError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="two-col">
      <form onSubmit={onSubmit} className="stack" style={{ maxWidth: "28rem" }}>
        {mode === "register" && (
          <div className="field">
            <label htmlFor="full_name">{d.fullName}</label>
            <input id="full_name" type="text" autoComplete="name" required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
          </div>
        )}
        <div className="field">
          <label htmlFor="email">{d.email}</label>
          <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="password">{d.password}</label>
          <input id="password" type="password" required minLength={mode === "register" ? 10 : 1} value={password}
                 onChange={(e) => setPassword(e.target.value)}
                 autoComplete={mode === "register" ? "new-password" : "current-password"}
                 aria-describedby={mode === "register" ? "pw-hint" : undefined} />
          {mode === "register" && <small id="pw-hint" className="hint">{d.passwordHint}</small>}
        </div>
        {error && <p className="notice error" role="alert">{error}</p>}
        <button type="submit" className="primary" disabled={busy}>{mode === "login" ? d.login : d.register}</button>
        <p>
          {mode === "login" ? d.haveNoAccount : d.haveAccount}{" "}
          <Link href={`/${mode === "login" ? "register" : "login"}${qs}`}>{mode === "login" ? d.register : d.login}</Link>
        </p>
      </form>
      {mode === "login" && showDemo && (
        <aside className="panel stack">
          <h2 style={{ fontSize: "1.3rem" }}>{d.demoTitle}</h2>
          <p className="muted">{d.demoHint}</p>
          <div className="choice-list">
            {([["donor", d.demoDonor], ["editor", d.demoEditor], ["admin", d.demoAdmin]] as const).map(([who, label]) => (
              <button key={who} type="button" onClick={() => { setEmail(`${who}@demo.example`); setPassword(DEMO_PASSWORD); }}>
                {label}: {who}@demo.example
              </button>
            ))}
          </div>
        </aside>
      )}
    </div>
  );
}
