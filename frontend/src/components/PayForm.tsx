"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Dict, Lang } from "@/lib/i18n";
import { TEST_CARDS } from "@/lib/testCards";

/** The test-mode stand-in for a hosted payment page. The API decides what happens to each card. */
export function PayForm({ d, lang, donationId, label }: { d: Dict; lang: Lang; donationId: string; label: string }) {
  const router = useRouter();
  const [card, setCard] = useState("");
  const [country, setCountry] = useState("IN");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (card.replace(/\D/g, "").length < 12) return setError(d.cardError);
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`/api/v1/donations/${donationId}/test-charge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_number: card, issuing_country: country }),
      });
      if (r.status === 422) return setError(d.cardError);
      if (!r.ok) throw new Error(String(r.status));
      router.refresh();
    } catch {
      setError(d.netError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="stack">
      <fieldset className="testcards">
        <legend style={{ fontWeight: 600 }}>{d.testCards}</legend>
        {TEST_CARDS.map((c) => (
          <button key={c.number} type="button" onClick={() => { setCard(c.number); setError(null); }}>
            <code>{c.number}</code><span className="muted">{c[lang]}</span>
          </button>
        ))}
      </fieldset>
      <div className="field">
        <label htmlFor="card">{d.cardNumber}</label>
        <input id="card" type="text" inputMode="numeric" autoComplete="off" value={card} onChange={(e) => setCard(e.target.value)}
               aria-invalid={Boolean(error)} aria-describedby={error ? "card-err" : undefined} />
        {error && <span id="card-err" className="field-error" role="alert">{error}</span>}
      </div>
      <div className="field">
        <label htmlFor="country">{d.cardCountry}</label>
        <select id="country" value={country} onChange={(e) => setCountry(e.target.value)}>
          <option value="IN">{d.countryIN}</option>
          <option value="XX">{d.countryOther}</option>
        </select>
      </div>
      <button type="submit" className="primary" disabled={busy}>{busy ? d.paying : label}</button>
    </form>
  );
}
