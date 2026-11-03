"use client";

import { useActionState } from "react";
import { runMonthly } from "@/app/admin/actions";

export function RunMonthly() {
  const [state, run, pending] = useActionState(runMonthly, null);
  return (
    <form action={run} className="stack">
      <button type="submit" disabled={pending}>Run today&apos;s monthly charges</button>
      {state?.error && <p className="notice error" role="alert">{state.error}</p>}
      {state?.note && <p className="notice ok" role="status">{state.note}</p>}
    </form>
  );
}
