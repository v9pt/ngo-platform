"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Dict } from "@/lib/i18n";

export function AuthForm({ d, mode }: { d: Dict; mode: "login" | "register" }) {
  const router = useRouter();
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body: Record<string, string> = {
      email: String(f.get("email") ?? ""),
      password: String(f.get("password") ?? ""),
    };
    if (mode === "register") body.full_name = String(f.get("full_name") ?? "");
    setBusy(true);
    setError(false);
    try {
      const r = await fetch(`/api/v1/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(String(r.status));
      router.push("/account");
      router.refresh();
    } catch {
      setError(true);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ maxWidth: "26rem" }}>
      {mode === "register" && (
        <div className="field">
          <label htmlFor="full_name">{d.fullName}</label>
          <input id="full_name" name="full_name" type="text" autoComplete="name" required maxLength={120} />
        </div>
      )}
      <div className="field">
        <label htmlFor="email">{d.email}</label>
        <input id="email" name="email" type="email" autoComplete="email" required />
      </div>
      <div className="field">
        <label htmlFor="password">{d.password}</label>
        <input
          id="password" name="password" type="password" required minLength={mode === "register" ? 10 : 1}
          autoComplete={mode === "register" ? "new-password" : "current-password"}
          aria-describedby={mode === "register" ? "pw-hint" : undefined}
        />
        {mode === "register" && <small id="pw-hint" className="muted">{d.passwordHint}</small>}
      </div>
      {error && <p role="alert">{d.authError}</p>}
      <button type="submit" className="primary" disabled={busy}>{mode === "login" ? d.login : d.register}</button>
    </form>
  );
}
