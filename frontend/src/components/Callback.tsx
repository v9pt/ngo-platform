"use client";

import { useId, useState } from "react";
import type { Dict, Lang } from "@/lib/i18n";

/** Every result offers a person to talk to. Typed values survive a failed attempt. */
export function Callback({ d, lang, schemeCode, open = false }: { d: Dict; lang: Lang; schemeCode?: string; open?: boolean }) {
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<{ field: "phone" | "consent" | "form"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const id = useId();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const digits = phone.replace(/\D/g, "").replace(/^(91|0)(?=\d{10}$)/, "");
    if (!/^[6-9]\d{9}$/.test(digits)) return setError({ field: "phone", text: d.phoneError });
    if (!consent) return setError({ field: "consent", text: d.consentError });
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/v1/schemes/callbacks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: digits, name, scheme_code: schemeCode ?? null, language: lang, consent: true }),
      });
      if (r.status === 429) return setError({ field: "form", text: d.callLimit });
      if (!r.ok) throw new Error(String(r.status));
      setDone(true);
    } catch {
      setError({ field: "form", text: d.netError });
    } finally {
      setBusy(false);
    }
  }

  if (done) return <p className="notice ok" role="status">{d.callDone}</p>;
  return (
    <details className="more" open={open}>
      <summary>{d.callTitle}</summary>
      <form onSubmit={submit} noValidate className="stack" style={{ maxWidth: "28rem" }}>
        <p className="muted">{d.callIntro}</p>
        <div className="field">
          <label htmlFor={`phone-${id}`}>{d.phone}</label>
          <input id={`phone-${id}`} type="tel" inputMode="tel" autoComplete="tel" value={phone}
                 onChange={(e) => setPhone(e.target.value)} aria-invalid={error?.field === "phone"}
                 aria-describedby={error?.field === "phone" ? `phone-${id}-err` : undefined} />
          {error?.field === "phone" && <span id={`phone-${id}-err`} className="field-error" role="alert">{error.text}</span>}
        </div>
        <div className="field">
          <label htmlFor={`name-${id}`}>{d.yourName}</label>
          <input id={`name-${id}`} type="text" autoComplete="name" maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="check">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <span>{d.consent}</span>
          </label>
          {error?.field === "consent" && <span className="field-error" role="alert">{error.text}</span>}
        </div>
        {error?.field === "form" && <p className="notice error" role="alert">{error.text}</p>}
        <button type="submit" disabled={busy}>{d.callSubmit}</button>
      </form>
    </details>
  );
}
