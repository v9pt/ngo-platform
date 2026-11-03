"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import type { Campaign } from "@/lib/api";
import type { Dict, Lang } from "@/lib/i18n";

export function DonateForm({ d, lang, campaigns }: { d: Dict; lang: Lang; campaigns: Campaign[] }) {
  const router = useRouter();
  // One key per form mount: a double-click or network retry reuses it and cannot double-charge.
  const idemKey = useRef(crypto.randomUUID());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const rupees = Number(f.get("amount"));
    if (!Number.isFinite(rupees) || rupees < 100) return setError(d.amountMin);
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/v1/donations", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": idemKey.current },
        body: JSON.stringify({
          campaign_slug: String(f.get("campaign")),
          amount_paise: Math.round(rupees * 100),
          kind: String(f.get("kind")),
        }),
      });
      if (r.status === 401) return router.push("/login");
      if (!r.ok) throw new Error(String(r.status));
      const donation = (await r.json()) as { id: string };
      router.push(`/donate/pay/${donation.id}`);
    } catch {
      setError(d.loadError);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ maxWidth: "30rem" }}>
      <div className="field">
        <label htmlFor="campaign">{d.campaign}</label>
        <select id="campaign" name="campaign" required>
          {campaigns.map((c) => (
            <option key={c.slug} value={c.slug}>{lang === "hi" ? c.title_hi : c.title_en}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="amount">{d.amount}</label>
        <input id="amount" name="amount" type="number" inputMode="numeric" min={100} step={1} defaultValue={500}
               required aria-describedby="amount-hint" />
        <small id="amount-hint" className="muted">{d.amountMin}</small>
      </div>
      <fieldset className="field" style={{ border: 0, padding: 0 }}>
        <legend style={{ fontWeight: 600 }}>{d.donate}</legend>
        <label><input type="radio" name="kind" value="one_time" defaultChecked /> {d.oneTime}</label>{" "}
        <label><input type="radio" name="kind" value="monthly" /> {d.monthly}</label>
      </fieldset>
      {error && <p role="alert">{error}</p>}
      <button type="submit" className="primary" disabled={busy}>{d.donateNow}</button>
    </form>
  );
}
