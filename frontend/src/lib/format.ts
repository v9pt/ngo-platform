/** Display helpers shared by server and client components. */

export function rupees(paise: number): string {
  return `₹${new Intl.NumberFormat("en-IN", { minimumFractionDigits: paise % 100 ? 2 : 0 }).format(paise / 100)}`;
}

export function formatDate(iso: string, lang: "hi" | "en"): string {
  return new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", {
    day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Kolkata",
  }).format(new Date(iso));
}

/** Only same-site paths may be used as a post-login destination, so a crafted link cannot send
 * someone to another site after they sign in. */
export function safeNext(next: string | null | undefined): string | null {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) return null;
  return next;
}

/** A scheme's facts may have changed if nobody has looked at it for about six months. */
export function isStale(lastChecked: string, now: Date = new Date()): boolean {
  return now.getTime() - new Date(lastChecked).getTime() > 180 * 24 * 60 * 60 * 1000;
}

/** Fills {name} placeholders in a translated string. */
export function fill(text: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce((s, [k, v]) => s.replaceAll(`{${k}}`, String(v)), text);
}
