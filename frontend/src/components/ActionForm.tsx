"use client";

import { useActionState } from "react";
import type { ActionResult } from "@/app/admin/actions";

/** Runs a server action and shows its outcome in place. A failed save keeps what was typed and
 * says why, instead of throwing the editor onto an error page. */
export function ActionForm({ action, children, success, className, inline }: {
  action: (prev: ActionResult, form: FormData) => Promise<ActionResult>;
  children: React.ReactNode;
  success?: string;
  className?: string;
  inline?: boolean;
}) {
  const [state, run, pending] = useActionState(action, null);
  return (
    <form action={run} className={className} aria-busy={pending} style={inline ? { display: "contents" } : undefined}>
      {children}
      {state?.error && <p className="notice error" role="alert">{state.error}</p>}
      {state && !state.error && success && <p className="notice ok" role="status">{success}</p>}
    </form>
  );
}
