"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import type { Campaign } from "@/lib/api";
import { rupees } from "@/lib/format";
import type { Dict, Lang } from "@/lib/i18n";

const PRESETS = [500, 1000, 2500, 5000];
const PAN = /^[A-Z]{5}[0-9]{4}[A-Z]$/;

export function DonateForm({ d, lang, campaigns, panMasked, initialCampaign }: {
  d: Dict; lang: Lang; campaigns: Campaign[]; panMasked: string | null; initialCampaign?: string;
}) {
  const router = useRouter();
  // One key per form mount: a double-click or network retry reuses it and cannot create a second donation.
  const idemKey = useRef(crypto.randomUUID());
  const [campaign, setCampaign] = useState(campaigns.some((c) => c.slug === initialCampaign) ? initialCampaign! : campaigns[0].slug);
  const [amount, setAmount] = useState("1000");
  const [kind, setKind] = useState("one_time");
  const [pan, setPan] = useState("");
  const [changingPan, setChangingPan] = useState(!panMasked);
  const [error, setError] = useState<{ field: "amount" | "pan" | "form"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = Number(amount);
    if (!Number.isFinite(value) || value < 100) return setError({ field: "amount", text: d.amountMin });
    if (value > 10_000_000) return setError({ field: "amount", text: d.amountMax });
    const cleanPan = pan.replace(/\s/g, "").toUpperCase();
    if (cleanPan && !PAN.test(cleanPan)) return setError({ field: "pan", text: d.panError });
    setBusy(true);
    setError(null);
    try {
      // The PAN goes first: the receipt is a snapshot taken at payment and can never change later.
      if (cleanPan) {
        const saved = await fetch("/api/v1/auth/me/pan", {
          method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pan: cleanPan }),
        });
        if (saved.status === 401) return router.push("/login?next=/donate");
        if (saved.status === 422) return setError({ field: "pan", text: d.panError });
        if (!saved.ok) throw new Error(String(saved.status));
      }
      const r = await fetch("/api/v1/donations", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": idemKey.current },
        body: JSON.stringify({ campaign_slug: campaign, amount_paise: Math.round(value * 100), kind }),
      });
      if (r.status === 401) return router.push("/login?next=/donate");
      if (!r.ok) throw new Error(String(r.status));
      router.push(`/donate/pay/${((await r.json()) as { id: string }).id}`);
    } catch {
      setError({ field: "form", text: d.netError });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="stack-l">
      <fieldset className="field">
        <legend>{d.campaign}</legend>
        <div className="choice-list">
          {campaigns.map((c) => (
            <label key={c.slug} className="choice">
              <input type="radio" name="campaign" checked={campaign === c.slug} onChange={() => setCampaign(c.slug)} />
              <span style={{ flex: 1 }}>
                <strong>{lang === "hi" ? c.title_hi : c.title_en}</strong><br />
                <span className="muted">{(lang === "hi" && c.description_hi) || c.description_en}</span><br />
                <small>{rupees(c.raised_paise)} {d.raised}{c.goal_paise ? `, ${d.goal} ${rupees(c.goal_paise)}` : ""}</small>
                {c.goal_paise ? <progress max={c.goal_paise} value={Math.min(c.raised_paise, c.goal_paise)} aria-hidden="true" style={{ marginTop: "0.4rem" }} /> : null}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="field">
        <span className="label" id="amount-label">{d.amount}</span>
        <div className="presets" role="group" aria-labelledby="amount-label">
          {PRESETS.map((p) => (
            <button key={p} type="button" aria-pressed={amount === String(p)} onClick={() => setAmount(String(p))}>{rupees(p * 100)}</button>
          ))}
        </div>
        <label htmlFor="amount" className="muted" style={{ fontWeight: 500 }}>{d.otherAmount}</label>
        <input id="amount" type="number" inputMode="numeric" min={100} step={1} value={amount} onChange={(e) => setAmount(e.target.value)}
               style={{ maxWidth: "14rem" }} aria-invalid={error?.field === "amount"} aria-describedby="amount-hint" />
        {error?.field === "amount"
          ? <span id="amount-hint" className="field-error" role="alert">{error.text}</span>
          : <small id="amount-hint" className="hint">{d.amountMin}</small>}
      </div>

      <fieldset className="field">
        <legend>{d.frequency}</legend>
        <div className="row">
          <label className="check"><input type="radio" name="kind" checked={kind === "one_time"} onChange={() => setKind("one_time")} /> {d.oneTime}</label>
          <label className="check"><input type="radio" name="kind" checked={kind === "monthly"} onChange={() => setKind("monthly")} /> {d.monthly}</label>
        </div>
        {kind === "monthly" && <small className="hint">{d.monthlyHint}</small>}
      </fieldset>

      <div className="field">
        <span className="label">{d.panTitle}</span>
        {panMasked && !changingPan ? (
          <p>{d.panOnFile}: <strong>{panMasked}</strong>{" "}
            <button type="button" className="link" onClick={() => setChangingPan(true)}>{d.panChange}</button></p>
        ) : (
          <>
            <label htmlFor="pan" className="visually-hidden">{d.panLabel}</label>
            <input id="pan" type="text" autoCapitalize="characters" autoComplete="off" maxLength={14} placeholder="ABCDE1234F" value={pan}
                   onChange={(e) => setPan(e.target.value)} style={{ maxWidth: "14rem" }}
                   aria-invalid={error?.field === "pan"} aria-describedby="pan-hint" />
            {error?.field === "pan" && <span className="field-error" role="alert">{error.text}</span>}
            <small id="pan-hint" className="hint">{d.panHint}</small>
          </>
        )}
      </div>

      {error?.field === "form" && <p className="notice error" role="alert">{error.text}</p>}
      <button type="submit" className="primary" disabled={busy}>{d.donateNow}</button>
    </form>
  );
}
