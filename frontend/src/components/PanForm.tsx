"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Dict } from "@/lib/i18n";

export function PanForm({ d, masked }: { d: Dict; masked: string | null }) {
  const router = useRouter();
  const [pan, setPan] = useState("");
  const [editing, setEditing] = useState(!masked);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const clean = pan.replace(/\s/g, "").toUpperCase();
    if (!/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(clean)) return setError(d.panError);
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/v1/auth/me/pan", {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pan: clean }),
      });
      if (r.status === 422) return setError(d.panError);
      if (!r.ok) throw new Error(String(r.status));
      setSaved(true); setEditing(false); setPan("");
      router.refresh();
    } catch {
      setError(d.netError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      {saved && <p className="notice ok" role="status">{d.panSaved}</p>}
      {masked && !editing && (
        <p>{d.panOnFile}: <strong>{masked}</strong>{" "}
          <button type="button" className="link" onClick={() => setEditing(true)}>{d.panChange}</button></p>
      )}
      {editing && (
        <form onSubmit={onSubmit} noValidate className="stack">
          <div className="field">
            <label htmlFor="account-pan">{d.panLabel}</label>
            <input id="account-pan" type="text" autoComplete="off" autoCapitalize="characters" maxLength={14} placeholder="ABCDE1234F"
                   value={pan} onChange={(e) => setPan(e.target.value)} style={{ maxWidth: "14rem" }}
                   aria-invalid={Boolean(error)} aria-describedby="account-pan-hint" />
            {error && <span className="field-error" role="alert">{error}</span>}
            <small id="account-pan-hint" className="hint">{d.panHint}</small>
          </div>
          <button type="submit" disabled={busy}>{d.panSave}</button>
        </form>
      )}
    </div>
  );
}
