"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Dict } from "@/lib/i18n";

/** Asks once before stopping, since the donor may have tapped by accident on a phone. */
export function CancelMandate({ d, id }: { d: Dict; id: string }) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  async function cancel() {
    setBusy(true);
    setError(false);
    try {
      const r = await fetch(`/api/v1/mandates/${id}/cancel`, { method: "POST" });
      if (!r.ok) throw new Error(String(r.status));
      router.refresh();
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

  if (!confirming) return <button type="button" onClick={() => setConfirming(true)}>{d.cancelMonthly}</button>;
  return (
    <div className="row">
      <button type="button" className="primary" onClick={cancel} disabled={busy}>{d.cancelConfirm}</button>
      <button type="button" onClick={() => setConfirming(false)}>{d.keepMonthly}</button>
      {error && <span className="field-error" role="alert">{d.netError}</span>}
    </div>
  );
}
